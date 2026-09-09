from pathlib import Path
from lastro.inventory import build_inventory

def test_inventory_detects_duplicate(tmp_path: Path):
    (tmp_path / "a.txt").write_text("same", encoding="utf-8")
    (tmp_path / "b.txt").write_text("same", encoding="utf-8")
    records, summary = build_inventory(tmp_path)
    assert len(records) == 2
    assert summary["duplicate_groups"] == 1
    assert records[0].duplicate_group == records[1].duplicate_group
