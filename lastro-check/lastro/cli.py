from __future__ import annotations
import argparse, json
from decimal import Decimal
from pathlib import Path
from .inventory import build_inventory, write_inventory
from .licensing import generate_keypair, issue_license, verify_license
from .reconcile import read_csv, reconcile, write_reconciliation
from .report import reconciliation_html
from . import __version__
from .provenance import SourceRef, source_ref_for_file, provenance_manifest, write_provenance_manifest, sha256_file


def main() -> None:
    p = argparse.ArgumentParser(prog="lastro", description="Lastro Check commercial toolkit")
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("reconcile", help="reconcile sales, acquirer and bank CSVs")
    r.add_argument("--sales", required=True)
    r.add_argument("--acquirer", required=True)
    r.add_argument("--bank", required=True)
    r.add_argument("--out", required=True)
    r.add_argument("--amount-tolerance", default="0.05")
    r.add_argument("--settlement-grace-days", type=int, default=1)
    r.add_argument("--bank-date-window-days", type=int, default=3)

    i = sub.add_parser("inventory", help="create SHA-256 document inventory")
    i.add_argument("--root", required=True)
    i.add_argument("--out", required=True)

    kg = sub.add_parser("license-keygen", help="generate Ed25519 commercial licensing keypair")
    kg.add_argument("--private", required=True)
    kg.add_argument("--public", required=True)

    li = sub.add_parser("license-issue", help="issue signed offline license")
    li.add_argument("--private", required=True)
    li.add_argument("--license", required=True)
    li.add_argument("--customer", required=True)
    li.add_argument("--product", default="Lastro Check")
    li.add_argument("--expires", required=True)
    li.add_argument("--seats", type=int, default=1)
    li.add_argument("--feature", action="append", default=[])

    lv = sub.add_parser("license-verify", help="verify signed offline license")
    lv.add_argument("--public", required=True)
    lv.add_argument("--license", required=True)

    args = p.parse_args()
    if args.cmd == "reconcile":
        refs = [source_ref_for_file(Path(f), locator="CSV header and all records", adapter="csv", adapter_version=__version__) for f in (args.sales, args.acquirer, args.bank)]
        out = Path(args.out); out.mkdir(parents=True, exist_ok=False)
        rows, summary = reconcile(read_csv(args.sales), read_csv(args.acquirer), read_csv(args.bank), Decimal(args.amount_tolerance), args.settlement_grace_days, args.bank_date_window_days)
        if any(sha256_file(Path(f)) != ref.source_sha256 for f, ref in zip((args.sales, args.acquirer, args.bank), refs)):
            raise ValueError("input changed during reconciliation")
        write_reconciliation(rows, out / "reconciliation.csv")
        (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        reconciliation_html(summary, out / "report.html")
        write_provenance_manifest(provenance_manifest(engine_version=__version__, sources=refs, outputs=list(out.iterdir())), out / "provenance.json")
        print(json.dumps(summary, ensure_ascii=False))
    elif args.cmd == "inventory":
        root, out = Path(args.root).resolve(), Path(args.out).resolve()
        if out == root or root in out.parents:
            raise ValueError("inventory output must be outside input tree")
        records, summary = build_inventory(args.root)
        if not records:
            raise ValueError("inventory needs at least one source")
        refs = [SourceRef(source_name=Path(r.relative_path).name, source_sha256=r.sha256, locator=r.relative_path, adapter="inventory", adapter_version=__version__) for r in records]
        write_inventory(records, summary, args.out)
        write_provenance_manifest(provenance_manifest(engine_version=__version__, sources=refs, outputs=list(out.iterdir())), out / "provenance.json")
        print(json.dumps(summary, ensure_ascii=False))
    elif args.cmd == "license-keygen":
        generate_keypair(args.private, args.public)
        print("keypair generated")
    elif args.cmd == "license-issue":
        obj = issue_license(args.private, args.license, customer=args.customer, product=args.product, expires=args.expires, seats=args.seats, features=args.feature)
        print(json.dumps(obj["payload"], ensure_ascii=False))
    elif args.cmd == "license-verify":
        print(json.dumps(verify_license(args.public, args.license), ensure_ascii=False))

if __name__ == "__main__":
    main()
