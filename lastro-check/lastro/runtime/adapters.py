from __future__ import annotations

from contextlib import closing
import hashlib
import json
import sqlite3
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from .domain import LicenseEvidence, OfferPolicy, OrderRecord, PaymentEvidence

DEFAULT_VERIFIER_TIMEOUT_SECONDS = 10.0
_INVALID = object()


def _parse_aware_datetime(value: str) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed.astimezone(timezone.utc)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _strict_verified(value: Any) -> bool:
    return value is True


def _strict_int(value: Any) -> int | None:
    return value if type(value) is int else None


def _strict_text(value: Any) -> str | None:
    return value if isinstance(value, str) and value.strip() else None


def _optional_text(value: Any) -> str | None | object:
    if value is None:
        return None
    return value if isinstance(value, str) else _INVALID


@dataclass(frozen=True, slots=True)
class EvidencePaymentVerifier:
    def verify(self, order: OrderRecord, evidence: PaymentEvidence) -> bool:
        return evidence.verified is True and bool(evidence.provider.strip()) and bool(evidence.reference.strip()) and _parse_aware_datetime(evidence.confirmed_at) is not None and type(evidence.amount_minor) is int and evidence.amount_minor == order.amount_minor and evidence.currency.upper() == order.currency.upper()


@dataclass(frozen=True, slots=True)
class ExternalCommandPaymentVerifier:
    command_prefix: Sequence[str]
    event_path: Path
    timeout_seconds: float = DEFAULT_VERIFIER_TIMEOUT_SECONDS

    def __post_init__(self) -> None:
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")

    def verify(self, order: OrderRecord, evidence: PaymentEvidence) -> bool:
        if not self.command_prefix or not self.event_path.is_file() or self.event_path.is_symlink():
            return False
        try:
            proc = subprocess.run([*self.command_prefix, str(self.event_path)], check=False, capture_output=True, text=True, timeout=self.timeout_seconds)
        except (OSError, subprocess.TimeoutExpired):
            return False
        if proc.returncode != 0:
            return False
        try:
            payload = json.loads(proc.stdout)
        except json.JSONDecodeError:
            return False
        if not isinstance(payload, dict) or not _strict_verified(payload.get("verified")):
            return False
        payment = payload.get("payment")
        if not isinstance(payment, dict) or payment.get("order_id") != order.order_id:
            return False
        provider = _strict_text(payment.get("provider")); reference = _strict_text(payment.get("reference")); amount_minor = _strict_int(payment.get("amount_minor")); currency = _strict_text(payment.get("currency")); confirmed_at = _strict_text(payment.get("confirmed_at"))
        if None in (provider, reference, amount_minor, currency, confirmed_at):
            return False
        if not isinstance(payload.get("event_sha256"), str) or payload["event_sha256"] != _sha256_file(self.event_path):
            return False
        try:
            verified_evidence = PaymentEvidence(provider, reference, amount_minor, currency, confirmed_at, True)
        except (TypeError, ValueError):
            return False
        return verified_evidence == evidence and EvidencePaymentVerifier().verify(order, verified_evidence)


class InMemoryPaymentReferenceStore:
    def __init__(self) -> None:
        self._claims: dict[tuple[str, str], str] = {}

    def claim(self, provider: str, reference: str, order_id: str) -> bool:
        key = (provider.strip().lower(), reference.strip())
        existing = self._claims.get(key)
        if existing is None:
            self._claims[key] = order_id
            return True
        return existing == order_id


class SqlitePaymentReferenceStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.path)) as conn, conn:
            conn.execute("CREATE TABLE IF NOT EXISTS payment_reference_claims (provider TEXT NOT NULL, reference TEXT NOT NULL, order_id TEXT NOT NULL, PRIMARY KEY(provider, reference))")

    def claim(self, provider: str, reference: str, order_id: str) -> bool:
        provider_key = provider.strip().lower(); reference_key = reference.strip()
        with closing(sqlite3.connect(self.path, isolation_level="IMMEDIATE")) as conn, conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("SELECT order_id FROM payment_reference_claims WHERE provider=? AND reference=?", (provider_key, reference_key)).fetchone()
            if row is not None:
                return row[0] == order_id
            conn.execute("INSERT INTO payment_reference_claims(provider, reference, order_id) VALUES (?, ?, ?)", (provider_key, reference_key, order_id))
            return True


@dataclass(frozen=True, slots=True)
class EvidenceLicenseVerifier:
    def verify(self, order: OrderRecord, policy: OfferPolicy, evidence: LicenseEvidence) -> bool:
        if evidence.verified is not True or not evidence.reference.strip() or evidence.product != policy.product_code or evidence.customer != order.customer:
            return False
        if policy.named_project_required and evidence.project != order.project:
            return False
        if policy.require_license_expiry:
            expiry = _parse_aware_datetime(evidence.expires_at or "")
            if expiry is None or expiry <= datetime.now(timezone.utc):
                return False
        elif evidence.expires_at and _parse_aware_datetime(evidence.expires_at) is None:
            return False
        return True


@dataclass(frozen=True, slots=True)
class ExternalCommandLicenseVerifier:
    command_prefix: Sequence[str]
    license_path: Path
    timeout_seconds: float = DEFAULT_VERIFIER_TIMEOUT_SECONDS

    def __post_init__(self) -> None:
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")

    def verify(self, order: OrderRecord, policy: OfferPolicy, evidence: LicenseEvidence) -> bool:
        if not self.command_prefix or not self.license_path.is_file() or self.license_path.is_symlink():
            return False
        try:
            proc = subprocess.run([*self.command_prefix, str(self.license_path)], check=False, capture_output=True, text=True, timeout=self.timeout_seconds)
        except (OSError, subprocess.TimeoutExpired):
            return False
        if proc.returncode != 0:
            return False
        try:
            payload = json.loads(proc.stdout)
        except json.JSONDecodeError:
            return False
        if not isinstance(payload, dict) or not _strict_verified(payload.get("verified")):
            return False
        claims = payload.get("claims")
        if not isinstance(claims, dict):
            return False
        reference = _strict_text(claims.get("reference")); product = _strict_text(claims.get("product")); customer = _strict_text(claims.get("customer")); project = _optional_text(claims.get("project")); expires_at = _optional_text(claims.get("expires_at"))
        if reference is None or product is None or customer is None or project is _INVALID or expires_at is _INVALID:
            return False
        if not isinstance(payload.get("license_sha256"), str) or payload["license_sha256"] != _sha256_file(self.license_path):
            return False
        try:
            guard_evidence = LicenseEvidence(reference, product, customer, project, expires_at, True)
        except (TypeError, ValueError):
            return False
        return guard_evidence == evidence and EvidenceLicenseVerifier().verify(order, policy, guard_evidence)
