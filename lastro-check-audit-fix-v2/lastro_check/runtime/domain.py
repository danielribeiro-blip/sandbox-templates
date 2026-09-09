from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class OrderState(str, Enum):
    DRAFT = "draft"
    QUALIFIED = "qualified"
    AWAITING_PAYMENT = "awaiting_payment"
    PAID = "paid"
    READY_FOR_FULFILLMENT = "ready_for_fulfillment"
    FULFILLED = "fulfilled"
    ACCEPTED = "accepted"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class OfferPolicy:
    code: str
    amount_minor: int
    currency: str
    product_code: str
    require_license_before_fulfillment: bool
    named_project_required: bool = True
    require_license_expiry: bool = True

    def __post_init__(self) -> None:
        if not self.code.strip():
            raise ValueError("offer code is required")
        if self.amount_minor <= 0:
            raise ValueError("offer amount_minor must be positive")
        if not self.currency.strip():
            raise ValueError("offer currency is required")
        object.__setattr__(self, "currency", self.currency.strip().upper())
        if not self.product_code.strip():
            raise ValueError("offer product_code is required")
        if not self.require_license_before_fulfillment and self.require_license_expiry:
            object.__setattr__(self, "require_license_expiry", False)


@dataclass(frozen=True, slots=True)
class PaymentEvidence:
    provider: str
    reference: str
    amount_minor: int
    currency: str
    confirmed_at: str
    verified: bool


@dataclass(frozen=True, slots=True)
class LicenseEvidence:
    reference: str
    product: str
    customer: str
    project: str | None
    expires_at: str | None
    verified: bool


@dataclass(frozen=True, slots=True)
class ArtifactRef:
    path: str
    sha256: str
    size_bytes: int


@dataclass(slots=True)
class OrderRecord:
    order_id: str
    offer_code: str
    product_code: str
    customer: str
    project: str | None
    amount_minor: int
    currency: str
    state: OrderState = OrderState.DRAFT
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
    payment: PaymentEvidence | None = None
    license: LicenseEvidence | None = None
    fulfillment_receipt: str | None = None
    accepted_at: str | None = None
    cancelled_at: str | None = None
    audit_log: list[dict[str, str]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def touch(self) -> None:
        self.updated_at = utc_now_iso()
