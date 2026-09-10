import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

from lastro.runtime.adapters import (
    EvidenceLicenseVerifier,
    EvidencePaymentVerifier,
    ExternalCommandLicenseVerifier,
    ExternalCommandPaymentVerifier,
    InMemoryPaymentReferenceStore,
    SqlitePaymentReferenceStore,
)
from lastro.runtime.catalog import OfferCatalogError, load_offer_policies
from lastro.runtime.domain import LicenseEvidence, OfferPolicy, OrderRecord, OrderState, PaymentEvidence
from lastro.runtime.service import CommercialRuntime, RuntimeInvariantError


PILOT = OfferPolicy(
    code="pilot",
    amount_minor=490000,
    currency="BRL",
    product_code="Lastro Check",
    require_license_before_fulfillment=False,
    require_license_expiry=False,
)
LICENSE = OfferPolicy(
    code="license",
    amount_minor=2490000,
    currency="BRL",
    product_code="Lastro Check",
    require_license_before_fulfillment=True,
    require_license_expiry=True,
)


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.store = InMemoryPaymentReferenceStore()
        self.runtime = CommercialRuntime(
            policies={"pilot": PILOT, "license": LICENSE},
            payment_verifier=EvidencePaymentVerifier(),
            license_verifier=EvidenceLicenseVerifier(),
            payment_reference_store=self.store,
        )

    def order_for(self, offer="pilot", order_id="ord-1"):
        policy = {"pilot": PILOT, "license": LICENSE}[offer]
        return OrderRecord(
            order_id,
            offer,
            policy.product_code,
            "Acme",
            "Project A",
            policy.amount_minor,
            policy.currency,
        )

    def paid_order(self, offer="pilot", order_id="ord-1", payment_ref=None):
        order = self.order_for(offer, order_id)
        self.runtime.qualify(order)
        self.runtime.request_payment(order)
        self.runtime.confirm_payment(
            order,
            PaymentEvidence(
                provider="provider",
                reference=payment_ref or f"pay-{order_id}",
                amount_minor=order.amount_minor,
                currency=order.currency,
                confirmed_at="2026-09-08T12:00:00Z",
                verified=True,
            ),
        )
        return order

    def test_unpaid_order_cannot_fulfill(self):
        order = self.order_for()
        self.runtime.qualify(order)
        self.runtime.request_payment(order)
        with self.assertRaises(RuntimeInvariantError):
            self.runtime.authorize_fulfillment(order)

    def test_pilot_can_fulfill_after_verified_payment_without_license(self):
        order = self.paid_order("pilot")
        self.runtime.authorize_fulfillment(order)
        self.assertEqual(order.state, OrderState.READY_FOR_FULFILLMENT)
        self.assertIsNone(order.license)

    def test_offer_amount_currency_and_product_are_canonical(self):
        bad_amount = OrderRecord("a", "license", LICENSE.product_code, "Acme", "Project A", 1, "BRL")
        bad_currency = OrderRecord("b", "license", LICENSE.product_code, "Acme", "Project A", LICENSE.amount_minor, "USD")
        bad_product = OrderRecord("c", "license", "Other Product", "Acme", "Project A", LICENSE.amount_minor, "BRL")
        for order in (bad_amount, bad_currency, bad_product):
            with self.subTest(order=order):
                with self.assertRaises(RuntimeInvariantError):
                    self.runtime.qualify(order)

    def test_license_offer_requires_correct_current_license(self):
        for evidence in (
            None,
            LicenseEvidence("lic-1", "Other Product", "Acme", "Project A", "2099-01-01T00:00:00Z", True),
            LicenseEvidence("lic-1", "Lastro Check", "Acme", "Project A", "2000-01-01T00:00:00Z", True),
            LicenseEvidence("lic-1", "Lastro Check", "Other", "Project A", "2099-01-01T00:00:00Z", True),
            LicenseEvidence("lic-1", "Lastro Check", "Acme", "Other Project", "2099-01-01T00:00:00Z", True),
        ):
            order = self.paid_order("license", order_id=f"ord-{id(evidence)}")
            with self.subTest(evidence=evidence):
                with self.assertRaises(RuntimeInvariantError):
                    self.runtime.authorize_fulfillment(order, evidence)

        good = self.paid_order("license", order_id="ord-good-license")
        self.runtime.authorize_fulfillment(
            good,
            LicenseEvidence(
                "lic-good",
                "Lastro Check",
                "Acme",
                "Project A",
                "2099-01-01T00:00:00Z",
                True,
            ),
        )
        self.assertEqual(good.state, OrderState.READY_FOR_FULFILLMENT)

    def test_payment_timestamp_must_be_timezone_aware_and_parseable(self):
        bad_times = ("", "not-a-date", "2026-09-08T12:00:00")
        for index, confirmed_at in enumerate(bad_times):
            order = self.order_for(order_id=f"ord-time-{index}")
            self.runtime.qualify(order)
            self.runtime.request_payment(order)
            evidence = PaymentEvidence(
                "provider",
                f"ref-{index}",
                order.amount_minor,
                order.currency,
                confirmed_at,
                True,
            )
            with self.subTest(confirmed_at=confirmed_at):
                with self.assertRaises(RuntimeInvariantError):
                    self.runtime.confirm_payment(order, evidence)

    def test_payment_reference_cannot_be_reused_for_different_order(self):
        self.paid_order("pilot", order_id="ord-a", payment_ref="shared-ref")
        other = self.order_for("pilot", "ord-b")
        self.runtime.qualify(other)
        self.runtime.request_payment(other)
        with self.assertRaises(RuntimeInvariantError):
            self.runtime.confirm_payment(
                other,
                PaymentEvidence(
                    "provider",
                    "shared-ref",
                    other.amount_minor,
                    other.currency,
                    "2026-09-08T12:01:00Z",
                    True,
                ),
            )

    def test_sqlite_payment_reference_store_is_persistent_and_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "runtime.db"
            first = SqlitePaymentReferenceStore(path)
            self.assertTrue(first.claim("PSP", "ref-1", "order-a"))
            second = SqlitePaymentReferenceStore(path)
            self.assertTrue(second.claim("PSP", "ref-1", "order-a"))
            self.assertFalse(second.claim("PSP", "ref-1", "order-b"))

    def test_external_guard_requires_machine_readable_claims_bound_to_license_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            license_path = root / "license.json"
            license_path.write_text("signed-license-placeholder", encoding="utf-8")
            license_sha = hashlib.sha256(license_path.read_bytes()).hexdigest()
            script = root / "guard.py"
            payload = {
                "verified": True,
                "license_sha256": license_sha,
                "claims": {
                    "reference": "lic-guard",
                    "product": "Lastro Check",
                    "customer": "Acme",
                    "project": "Project A",
                    "expires_at": "2099-01-01T00:00:00Z",
                },
            }
            script.write_text(
                "import json\n"
                f"print(json.dumps({payload!r}))\n",
                encoding="utf-8",
            )
            verifier = ExternalCommandLicenseVerifier([sys.executable, str(script)], license_path)
            order = self.order_for("license", "ord-guard")
            good = LicenseEvidence(
                "lic-guard",
                "Lastro Check",
                "Acme",
                "Project A",
                "2099-01-01T00:00:00Z",
                True,
            )
            self.assertTrue(verifier.verify(order, LICENSE, good))
            rebound = LicenseEvidence(
                "lic-guard",
                "Lastro Check",
                "Acme",
                "Other Project",
                "2099-01-01T00:00:00Z",
                True,
            )
            self.assertFalse(verifier.verify(order, LICENSE, rebound))

            exit_only = root / "exit_only.py"
            exit_only.write_text("raise SystemExit(0)\n", encoding="utf-8")
            self.assertFalse(
                ExternalCommandLicenseVerifier([sys.executable, str(exit_only)], license_path).verify(
                    order, LICENSE, good
                )
            )


    def test_external_payment_verifier_requires_machine_readable_event_binding(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            event_path = root / "payment-event.json"
            event_path.write_text("provider-event-placeholder", encoding="utf-8")
            event_sha = hashlib.sha256(event_path.read_bytes()).hexdigest()
            script = root / "payment_guard.py"
            payload = {
                "verified": True,
                "event_sha256": event_sha,
                "payment": {
                    "order_id": "ord-auth-payment",
                    "provider": "provider",
                    "reference": "ref-auth",
                    "amount_minor": PILOT.amount_minor,
                    "currency": PILOT.currency,
                    "confirmed_at": "2026-09-08T12:00:00Z",
                },
            }
            script.write_text(
                "import json\n"
                f"print(json.dumps({payload!r}))\n",
                encoding="utf-8",
            )
            verifier = ExternalCommandPaymentVerifier([sys.executable, str(script)], event_path)
            order = self.order_for("pilot", "ord-auth-payment")
            evidence = PaymentEvidence(
                "provider",
                "ref-auth",
                PILOT.amount_minor,
                PILOT.currency,
                "2026-09-08T12:00:00Z",
                True,
            )
            self.assertTrue(verifier.verify(order, evidence))
            rebound = PaymentEvidence(
                "provider",
                "other-ref",
                PILOT.amount_minor,
                PILOT.currency,
                "2026-09-08T12:00:00Z",
                True,
            )
            self.assertFalse(verifier.verify(order, rebound))

    def test_payment_evidence_is_rechecked_and_offer_terms_cannot_change(self):
        order = self.paid_order("pilot")
        order.amount_minor = 999999
        with self.assertRaises(RuntimeInvariantError):
            self.runtime.authorize_fulfillment(order)

    def test_acceptance_and_cancellation_record_operational_evidence(self):
        order = self.paid_order("pilot", "ord-accept")
        self.runtime.authorize_fulfillment(order)
        order.state = OrderState.FULFILLED
        self.runtime.accept(order, actor="client", reference="acceptance-001")
        self.assertIsNotNone(order.accepted_at)
        self.assertEqual(order.audit_log[-1]["reference"], "acceptance-001")

        paid = self.paid_order("pilot", "ord-cancel")
        with self.assertRaises(RuntimeInvariantError):
            self.runtime.cancel(paid, actor="operator", reason="cancelled")
        self.runtime.cancel(
            paid,
            actor="operator",
            reason="cancelled",
            financial_disposition="refund_pending",
        )
        self.assertIsNotNone(paid.cancelled_at)
        self.assertEqual(paid.audit_log[-1]["reference"], "refund_pending")

    def test_state_machine_rejects_skips(self):
        order = self.order_for()
        with self.assertRaises(RuntimeInvariantError):
            self.runtime.request_payment(order)
        with self.assertRaises(RuntimeInvariantError):
            self.runtime.accept(order, actor="x", reference="y")

    def test_offer_catalog_is_executable_and_enforces_documented_values(self):
        base = Path(__file__).resolve().parents[1]
        catalog_path = base / "candidate" / "operations" / "offers.example.json"
        if not catalog_path.exists():
            catalog_path = base / "operations" / "offers.example.json"
        policies = load_offer_policies(catalog_path)
        self.assertEqual(policies["technical_pilot"].amount_minor, 490000)
        self.assertEqual(policies["technical_pilot"].currency, "BRL")
        self.assertEqual(policies["component_license_12m"].amount_minor, 2490000)
        self.assertEqual(policies["component_license_12m"].product_code, "Lastro Check")

        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "offers.json"
            bad.write_text(json.dumps({"offers": [{"code": "x"}]}), encoding="utf-8")
            with self.assertRaises(OfferCatalogError):
                load_offer_policies(bad)


if __name__ == "__main__":
    unittest.main()
