from __future__ import annotations
import base64, json, os
from datetime import date, datetime, timezone
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey


def _write_private_key(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # Create/truncate with owner-only permissions. chmod afterwards as a second
    # guard because umask and pre-existing files vary across platforms.
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
    finally:
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass


def generate_keypair(private_path: str | Path, public_path: str | Path) -> None:
    private = Ed25519PrivateKey.generate()
    private_bytes = private.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_bytes = private.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    private_path = Path(private_path)
    public_path = Path(public_path)
    if private_path.resolve() == public_path.resolve():
        raise ValueError("private and public key paths must differ")
    _write_private_key(private_path, private_bytes)
    public_path.parent.mkdir(parents=True, exist_ok=True)
    public_path.write_bytes(public_bytes)


def _canonical(payload: dict[str, object]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def issue_license(private_key_path: str | Path, license_path: str | Path, *, customer: str, product: str, expires: str, seats: int, features: list[str]) -> dict[str, object]:
    exp = date.fromisoformat(expires)
    if seats < 1:
        raise ValueError("seats must be >= 1")
    private = serialization.load_pem_private_key(Path(private_key_path).read_bytes(), password=None)
    if not isinstance(private, Ed25519PrivateKey):
        raise ValueError("private key is not Ed25519")
    payload = {
        "customer": customer,
        "product": product,
        "expires": exp.isoformat(),
        "seats": seats,
        "features": sorted(set(features)),
        "issued_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    sig = private.sign(_canonical(payload))
    obj = {"payload": payload, "signature": base64.b64encode(sig).decode("ascii"), "algorithm": "Ed25519"}
    Path(license_path).write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    return obj


def verify_license(public_key_path: str | Path, license_path: str | Path, *, today: date | None = None) -> dict[str, object]:
    return verify_license_bytes(public_key_path, Path(license_path).read_bytes(), today=today)


def verify_license_bytes(public_key_path: str | Path, raw: bytes, *, today: date | None = None) -> dict[str, object]:
    public = serialization.load_pem_public_key(Path(public_key_path).read_bytes())
    if not isinstance(public, Ed25519PublicKey):
        raise ValueError("public key is not Ed25519")
    obj = json.loads(raw)
    if obj.get("algorithm") != "Ed25519":
        raise ValueError("unsupported signature algorithm")
    payload = obj["payload"]
    sig = base64.b64decode(obj["signature"], validate=True)
    public.verify(sig, _canonical(payload))
    now = today or date.today()
    exp = date.fromisoformat(payload["expires"])
    return {"valid_signature": True, "expired": now > exp, "payload": payload}
