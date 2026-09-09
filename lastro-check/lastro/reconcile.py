from __future__ import annotations
import csv
from dataclasses import dataclass, asdict
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Iterable
from .money import money, fmt
from .reconciliation.matching_policy import MatchEvent, MatchPolicy, MatchStatus, decide_match
from .output_safety import write_safe_csv

DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y")

def parse_date(value: str | None) -> date | None:
    if not value:
        return None
    s = value.strip()
    for f in DATE_FORMATS:
        try:
            return datetime.strptime(s, f).date()
        except ValueError:
            pass
    raise ValueError(f"invalid date {value!r}; expected YYYY-MM-DD or DD/MM/YYYY")

def read_csv(path: str | Path) -> list[dict[str, str]]:
    with open(path, "r", newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))

@dataclass
class ReconRow:
    transaction_id: str
    sale_date: str
    expected_settlement_date: str
    acquirer_settlement_date: str
    gross_expected: str
    gross_acquirer: str
    fee_expected: str
    fee_charged: str
    net_expected: str
    net_acquirer: str
    bank_amount: str
    bank_posting_date: str
    acquirer_reference: str
    bank_reference: str
    status: str
    exceptions: str
    match_method: str = "NONE"

REQUIRED_SALES = {"transaction_id", "sale_date", "gross_amount", "fee_expected", "expected_settlement_date"}
REQUIRED_ACQ = {"transaction_id", "settlement_date", "gross_amount", "fee_charged", "net_amount", "acquirer_reference"}
REQUIRED_BANK = {"posting_date", "amount", "description", "reference"}

def _validate(rows: list[dict[str, str]], required: set[str], name: str) -> None:
    if not rows:
        raise ValueError(f"{name} is empty")
    missing = required - set(rows[0].keys())
    if missing:
        raise ValueError(f"{name} missing columns: {', '.join(sorted(missing))}")

def reconcile(
    sales_rows: list[dict[str, str]],
    acquirer_rows: list[dict[str, str]],
    bank_rows: list[dict[str, str]],
    amount_tolerance: Decimal = Decimal("0.05"),
    settlement_grace_days: int = 1,
    bank_date_window_days: int = 3,
) -> tuple[list[ReconRow], dict[str, object]]:
    _validate(sales_rows, REQUIRED_SALES, "sales")
    _validate(acquirer_rows, REQUIRED_ACQ, "acquirer")
    _validate(bank_rows, REQUIRED_BANK, "bank")

    policy = MatchPolicy(allow_heuristic=True, max_date_delta_days=bank_date_window_days)
    if not amount_tolerance.is_finite() or amount_tolerance < 0:
        raise ValueError("amount_tolerance must be finite and non-negative")
    acq_by_tx: dict[str, list[dict[str, str]]] = {}
    for row in acquirer_rows:
        acq_by_tx.setdefault(row["transaction_id"].strip(), []).append(row)

    bank_unused = list(range(len(bank_rows)))
    output: list[ReconRow] = []
    counts: dict[str, int] = {}
    financial_gap = Decimal("0")

    def bank_match(target: Decimal, target_date: date | None, reference: str) -> tuple[dict[str, str] | None, str]:
        if target_date is None:
            return None, "NONE"
        candidates = []
        for idx in bank_unused:
            row = bank_rows[idx]
            bdate = parse_date(row.get("posting_date"))
            if bdate is None or abs((bdate-target_date).days) > bank_date_window_days:
                continue
            if abs(money(row["amount"])-target) > amount_tolerance:
                continue
            candidates.append(MatchEvent(str(idx), bdate, (row.get("reference") or "").strip(), True))
        decision = decide_match(MatchEvent("target", target_date, reference.strip(), True), candidates, policy)
        if decision.status is not MatchStatus.MATCHED:
            return None, decision.status.value
        idx = int(decision.matched_event_id)
        bank_unused.remove(idx)
        return bank_rows[idx], decision.method.value

    for sale in sales_rows:
        tx = sale["transaction_id"].strip()
        gross = money(sale["gross_amount"])
        fee_exp = money(sale["fee_expected"])
        net_exp = gross - fee_exp
        exp_date = parse_date(sale["expected_settlement_date"])
        exceptions: list[str] = []
        match_method = "NONE"
        acq_list = acq_by_tx.get(tx, [])
        acq = acq_list[0] if acq_list else None
        if len(acq_list) > 1:
            exceptions.append("DUPLICATE_ACQUIRER")

        if not acq:
            exceptions.append("MISSING_ACQUIRER")
            acq_gross = fee_charged = net_acq = Decimal("0")
            acq_date = None
            acq_ref = ""
            bank = None
        else:
            acq_gross = money(acq["gross_amount"])
            fee_charged = money(acq["fee_charged"])
            net_acq = money(acq["net_amount"])
            acq_date = parse_date(acq["settlement_date"])
            acq_ref = acq.get("acquirer_reference", "")
            if abs(acq_gross - gross) > amount_tolerance:
                exceptions.append("GROSS_MISMATCH")
            if abs(fee_charged - fee_exp) > amount_tolerance:
                exceptions.append("FEE_MISMATCH")
            if abs(net_acq - net_exp) > amount_tolerance:
                exceptions.append("NET_MISMATCH")
            if exp_date and acq_date and acq_date > exp_date + timedelta(days=settlement_grace_days):
                exceptions.append("LATE_SETTLEMENT")
            bank, match_method = bank_match(net_acq, acq_date or exp_date, acq_ref)
            if match_method == "AMBIGUOUS":
                exceptions.append("BANK_AMBIGUOUS")
            if not bank:
                exceptions.append("BANK_MISSING")

        bank_amt = money(bank["amount"]) if bank else Decimal("0")
        bank_date = parse_date(bank["posting_date"]) if bank else None
        if bank and abs(bank_amt - net_acq) > amount_tolerance:
            exceptions.append("BANK_AMOUNT_MISMATCH")
        if acq:
            financial_gap += net_exp - bank_amt
        else:
            financial_gap += net_exp
        status = "OK" if not exceptions else "EXCEPTION"
        for ex in exceptions:
            counts[ex] = counts.get(ex, 0) + 1
        output.append(ReconRow(
            transaction_id=tx,
            sale_date=sale["sale_date"],
            expected_settlement_date=sale["expected_settlement_date"],
            acquirer_settlement_date=acq["settlement_date"] if acq else "",
            gross_expected=fmt(gross),
            gross_acquirer=fmt(acq_gross),
            fee_expected=fmt(fee_exp),
            fee_charged=fmt(fee_charged),
            net_expected=fmt(net_exp),
            net_acquirer=fmt(net_acq),
            bank_amount=fmt(bank_amt),
            bank_posting_date=bank["posting_date"] if bank else "",
            acquirer_reference=acq_ref,
            bank_reference=(bank.get("reference", "") if bank else ""),
            status=status,
            exceptions="|".join(exceptions),
            match_method=match_method,
        ))

    unmatched_bank_total = sum((money(bank_rows[i]["amount"]) for i in bank_unused), Decimal("0"))
    summary = {
        "transactions": len(sales_rows),
        "ok": sum(1 for r in output if r.status == "OK"),
        "exceptions": sum(1 for r in output if r.status != "OK"),
        "exception_counts": counts,
        "unmatched_bank_entries": len(bank_unused),
        "unmatched_bank_total": fmt(unmatched_bank_total),
        "potential_financial_gap": fmt(financial_gap),
        "amount_tolerance": fmt(amount_tolerance),
        "settlement_grace_days": settlement_grace_days,
        "bank_date_window_days": bank_date_window_days,
    }
    return output, summary

def write_reconciliation(rows: Iterable[ReconRow], path: str | Path) -> None:
    rows = list(rows)
    fieldnames = list(asdict(rows[0]).keys()) if rows else list(ReconRow.__annotations__.keys())
    write_safe_csv(Path(path), fieldnames=fieldnames, rows=(asdict(row) for row in rows),
                   untrusted_text_fields={"transaction_id", "acquirer_reference", "bank_reference", "sale_date", "expected_settlement_date", "acquirer_settlement_date", "bank_posting_date"})
