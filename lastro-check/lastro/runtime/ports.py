from __future__ import annotations

from typing import Protocol

from .domain import LicenseEvidence, OfferPolicy, OrderRecord, PaymentEvidence


class PaymentVerifier(Protocol):
    def verify(self, order: OrderRecord, evidence: PaymentEvidence) -> bool: ...


class PaymentReferenceStore(Protocol):
    def claim(self, provider: str, reference: str, order_id: str) -> bool: ...


class LicenseVerifier(Protocol):
    def verify(self, order: OrderRecord, policy: OfferPolicy, evidence: LicenseEvidence) -> bool: ...
