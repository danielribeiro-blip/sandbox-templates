from __future__ import annotations

import csv
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INPUT = ROOT / "input"
MANIFEST = ROOT / "manifest.csv"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


with MANIFEST.open(newline="", encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

errors = []
for row in rows:
    path = INPUT / row["relative_path"]
    actual = sha256(path)
    expected = row["sha256"]
    if actual != expected:
        errors.append((row["relative_path"], expected, actual))

if errors:
    for name, expected, actual in errors:
        print(f"FAIL {name}: expected={expected} actual={actual}")
    raise SystemExit(1)

print(f"PASS: {len(rows)} input files match the published manifest SHA-256 values")
