from pathlib import Path


def test_source_tree_contains_no_private_signing_key():
    root = Path(__file__).resolve().parents[1]
    forbidden_names = {"licensor-private.pem", "private.pem"}
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        assert path.name not in forbidden_names
        if path.suffix.lower() in {".pem", ".key"}:
            data = path.read_bytes()
            assert b"BEGIN PRIVATE KEY" not in data
            assert b"BEGIN ED25519 PRIVATE KEY" not in data
