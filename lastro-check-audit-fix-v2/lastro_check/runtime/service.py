from __future__ import annotations

from .domain import LicenseEvidence, OfferPolicy, OrderRecord, OrderState, PaymentEvidence, utc_now_iso
from .ports import LicenseVerifier, PaymentReferenceStore, PaymentVerifier


class RuntimeInvariantError(RuntimeError):
    pass


_ALLOWED = {
    OrderState.DRAFT: {OrderState.QUALIFIED, OrderState.CANCELLED},
    OrderState.QUALIFIED: {OrderState.AWAITING_PAYMENT, OrderState.CANCELLED},
    OrderState.AWAITING_PAYMENT: {OrderState.PAID, OrderState.CANCELLED},
    OrderState.PAID: {OrderState.READY_FOR_FULFILLMENT, OrderState.CANCELLED},
    OrderState.READY_FOR_FULFILLMENT: {OrderState.FULFILLED, OrderState.CANCELLED},
    OrderState.FULFILLED: {OrderState.ACCEPTED},
    OrderState.ACCEPTED: set(),
    OrderState.CANCELLED: set(),
}


class CommercialRuntime:
    """Deterministic commercial state machine around an existing Lastro engine."""

    def __init__(self, policies: dict[str, OfferPolicy], payment_verifier: PaymentVerifier, license_verifier: LicenseVerifier, payment_reference_store: PaymentReferenceStore) -> None:
        if not policies:
            raise ValueError("at least one offer policy is required")
        for key, policy in policies.items():
            if key != policy.code:
                raise ValueError(f"policy map key {key!r} does not match code {policy.code!r}")
        self._policies = dict(policies)
        self._payment_verifier = payment_verifier
        self._license_verifier = license_verifier
        self._payment_reference_store = payment_reference_store

    def _policy(self, order: OrderRecord) -> OfferPolicy:
        try:
            return self._policies[order.offer_code]
        except KeyError as exc:
            raise RuntimeInvariantError(f"unknown offer code: {order.offer_code}") from exc

    @staticmethod
    def _transition(order: OrderRecord, target: OrderState, *, actor: str = "runtime", reference: str = "", reason: str = "") -> None:
        if target not in _ALLOWED[order.state]:
            raise RuntimeInvariantError(f"invalid transition: {order.state.value} -> {target.value}")
        if not actor.strip():
            raise RuntimeInvariantError("transition actor is required")
        previous = order.state
        at = utc_now_iso()
        order.state = target
        order.updated_at = at
        order.audit_log.append({"from": previous.value, "to": target.value, "at": at, "actor": actor, "reference": reference, "reason": reason})

    def qualify(self, order: OrderRecord) -> OrderRecord:
        policy = self._policy(order)
        if not order.order_id.strip():
            raise RuntimeInvariantError("order id is required")
        if policy.named_project_required and not (order.project and order.project.strip()):
            raise RuntimeInvariantError("named project is required by offer policy")
        if not order.customer.strip():
            raise RuntimeInvariantError("customer is required")
        if order.product_code != policy.product_code:
            raise RuntimeInvariantError("order product does not match canonical offer policy")
        if order.amount_minor != policy.amount_minor:
            raise RuntimeInvariantError("order amount does not match canonical offer policy")
        if order.currency.upper() != policy.currency.upper():
            raise RuntimeInvariantError("order currency does not match canonical offer policy")
        self._transition(order, OrderState.QUALIFIED, reference=policy.code)
        return order

    def request_payment(self, order: OrderRecord) -> OrderRecord:
        self._transition(order, OrderState.AWAITING_PAYMENT)
        return order

    def confirm_payment(self, order: OrderRecord, evidence: PaymentEvidence) -> OrderRecord:
        if order.state is not OrderState.AWAITING_PAYMENT:
            raise RuntimeInvariantError("order is not awaiting payment")
        if not self._payment_verifier.verify(order, evidence):
            raise RuntimeInvariantError("payment evidence did not verify")
        if not self._payment_reference_store.claim(evidence.provider, evidence.reference, order.order_id):
            raise RuntimeInvariantError("payment provider/reference is already bound to another order")
        order.payment = evidence
        self._transition(order, OrderState.PAID, reference=f"{evidence.provider}:{evidence.reference}")
        return order

    def authorize_fulfillment(self, order: OrderRecord, license_evidence: LicenseEvidence | None = None) -> OrderRecord:
        if order.state is not OrderState.PAID:
            raise RuntimeInvariantError("payment must be verified before fulfillment")
        policy = self._policy(order)
        if order.product_code != policy.product_code or order.amount_minor != policy.amount_minor or order.currency.upper() != policy.currency.upper():
            raise RuntimeInvariantError("order commercial terms no longer match canonical offer policy")
        if order.payment is None or not self._payment_verifier.verify(order, order.payment):
            raise RuntimeInvariantError("stored payment evidence no longer matches the order")
        if policy.require_license_before_fulfillment:
            if license_evidence is None:
                raise RuntimeInvariantError("license evidence is required")
            if not self._license_verifier.verify(order, policy, license_evidence):
                raise RuntimeInvariantError("license evidence did not verify")
            order.license = license_evidence
        self._transition(order, OrderState.READY_FOR_FULFILLMENT)
        return order

    def mark_fulfilled(self, order: OrderRecord, receipt_path: str, *, expected_engine_version: str, expected_engine_distribution_sha256: str) -> OrderRecord:
        if not receipt_path.strip():
            raise RuntimeInvariantError("fulfillment receipt path is required")
        from .fulfillment import sha256_file, verify_receipt_for_order
        errors = verify_receipt_for_order(receipt_path, order, expected_engine_version=expected_engine_version, expected_engine_distribution_sha256=expected_engine_distribution_sha256)
        if errors:
            raise RuntimeInvariantError("fulfillment receipt did not verify: " + "; ".join(errors))
        receipt_sha256 = sha256_file(receipt_path)
        order.fulfillment_receipt = receipt_path
        order.fulfillment_receipt_sha256 = receipt_sha256
        self._transition(order, OrderState.FULFILLED, reference=f"{receipt_path}#sha256={receipt_sha256}")
        return order

    def accept(self, order: OrderRecord, *, actor: str, reference: str) -> OrderRecord:
        if not reference.strip():
            raise RuntimeInvariantError("acceptance reference is required")
        self._transition(order, OrderState.ACCEPTED, actor=actor, reference=reference)
        order.accepted_at = order.updated_at
        return order

    def cancel(self, order: OrderRecord, *, actor: str, reason: str, financial_disposition: str | None = None) -> OrderRecord:
        if not reason.strip():
            raise RuntimeInvariantError("cancellation reason is required")
        if order.payment is not None and not (financial_disposition and financial_disposition.strip()):
            raise RuntimeInvariantError("financial_disposition is required when cancelling an order with payment evidence")
        self._transition(order, OrderState.CANCELLED, actor=actor, reason=reason, reference=financial_disposition or "")
        order.cancelled_at = order.updated_at
        return order
