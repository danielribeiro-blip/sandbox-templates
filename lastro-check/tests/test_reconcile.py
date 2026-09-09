from decimal import Decimal
from lastro.reconcile import read_csv, reconcile

def test_demo_reconciliation():
    sales = read_csv("examples/sales.csv")
    acq = read_csv("examples/acquirer.csv")
    bank = read_csv("examples/bank.csv")
    rows, summary = reconcile(sales, acq, bank, Decimal("0.05"), 1)
    assert len(rows) == 4
    by_tx = {r.transaction_id: r for r in rows}
    assert by_tx["TX1001"].status == "OK"
    assert "FEE_MISMATCH" in by_tx["TX1002"].exceptions
    assert "LATE_SETTLEMENT" in by_tx["TX1003"].exceptions
    assert "BANK_MISSING" in by_tx["TX1003"].exceptions
    assert "MISSING_ACQUIRER" in by_tx["TX1004"].exceptions
    assert summary["exceptions"] == 3
