from datetime import date
from pathlib import Path
from lastro.licensing import generate_keypair, issue_license, verify_license

def test_license_roundtrip(tmp_path: Path):
    prv = tmp_path / "private.pem"; pub = tmp_path / "public.pem"; lic = tmp_path / "license.json"
    generate_keypair(prv, pub)
    issue_license(prv, lic, customer="Test", product="Lastro", expires="2030-01-01", seats=3, features=["reconciliation"])
    result = verify_license(pub, lic, today=date(2029, 1, 1))
    assert result["valid_signature"] is True
    assert result["expired"] is False
    assert result["payload"]["seats"] == 3
