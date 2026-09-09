from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


_PRIVATE_KEY_TYPES = (b"", b"RSA ", b"EC ", b"OPENSSH ", b"ENCRYPTED ", b"DSA ", b"ED25519 ")
PRIVATE_KEY_MARKERS = tuple(b"-----BEGIN " + key_type + b"PRIVATE KEY-----" for key_type in _PRIVATE_KEY_TYPES)
FORBIDDEN_NAME_PARTS = ("licensor-private", "private.pem", "private.key", "signing-key", "signing_key", "id_rsa", "id_ed25519", "client_secret", "client-secret")
FORBIDDEN_EXACT_NAMES = {"credentials.json", "secrets.json"}
FORBIDDEN_EXTENSIONS = {".key", ".p12", ".pfx", ".secret", ".secrets"}
SKIP_DIRS = {".venv", "venv", "__pycache__", ".pytest_cache"}
FORBIDDEN_REPOSITORY_METADATA = {".git"}


@dataclass(frozen=True, slots=True)
class DistributionFinding:
    path: str
    reason: str


class UnsafeDistributionError(RuntimeError):
    pass


def _iter_files(root: Path) -> Iterable[Path]:
    for path in root.rglob("*"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if any(part in FORBIDDEN_REPOSITORY_METADATA for part in path.parts):
            continue
        if path.is_file() or path.is_symlink():
            yield path


def _contains_private_key_marker(path: Path) -> bytes | None:
    max_marker = max(len(marker) for marker in PRIVATE_KEY_MARKERS)
    overlap = b""
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                return None
            data = overlap + chunk
            for marker in PRIVATE_KEY_MARKERS:
                if marker in data:
                    return marker
            overlap = data[-(max_marker - 1):]


def _filename_is_forbidden(path: Path) -> str | None:
    lower_name = path.name.lower()
    if lower_name == ".env" or lower_name.startswith(".env."):
        return f"forbidden environment filename: {lower_name}"
    if lower_name in FORBIDDEN_EXACT_NAMES:
        return f"forbidden sensitive filename: {lower_name}"
    if path.suffix.lower() in FORBIDDEN_EXTENSIONS:
        return f"forbidden sensitive extension: {path.suffix.lower()}"
    for forbidden in FORBIDDEN_NAME_PARTS:
        if forbidden in lower_name:
            return f"forbidden sensitive filename: {forbidden}"
    if lower_name.startswith("credentials.") or lower_name.startswith("secrets."):
        return f"forbidden sensitive filename: {lower_name}"
    return None


def scan_distribution(root: str | Path) -> list[DistributionFinding]:
    root_path = Path(root)
    if not root_path.exists():
        raise FileNotFoundError(root_path)
    if not root_path.is_dir():
        raise NotADirectoryError(root_path)
    findings: list[DistributionFinding] = []
    for candidate in root_path.rglob(".git"):
        findings.append(DistributionFinding(str(candidate), "repository metadata is not allowed in client staging: .git"))
    for path in _iter_files(root_path):
        if path.is_symlink():
            findings.append(DistributionFinding(str(path), "symlink is not allowed in client staging"))
            continue
        filename_reason = _filename_is_forbidden(path)
        if filename_reason:
            findings.append(DistributionFinding(str(path), filename_reason))
        try:
            marker = _contains_private_key_marker(path)
        except OSError as exc:
            findings.append(DistributionFinding(str(path), f"file could not be inspected: {exc}"))
            continue
        if marker is not None:
            findings.append(DistributionFinding(str(path), f"private key material detected: {marker.decode()}"))
    return findings


def assert_distribution_safe(root: str | Path) -> None:
    findings = scan_distribution(root)
    if findings:
        rendered = "\n".join(f"- {item.path}: {item.reason}" for item in findings)
        raise UnsafeDistributionError(f"distribution preflight failed:\n{rendered}")
