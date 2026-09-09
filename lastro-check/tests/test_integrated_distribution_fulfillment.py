import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from lastro.provenance import source_ref_for_file, provenance_manifest, write_provenance_manifest

from lastro.runtime.adapters import (
    EvidenceLicenseVerifier,
    EvidencePaymentVerifier,
    InMemoryPaymentReferenceStore,
)
from lastro.runtime.distribution import UnsafeDistributionError, assert_distribution_safe, scan_distribution
from lastro.runtime.domain import OfferPolicy, OrderRecord, PaymentEvidence
from lastro.runtime.fulfillment import (
    build_receipt,
    collect_artifacts,
    verify_receipt,
    verify_receipt_for_order,
    write_receipt,
)
from lastro.runtime.service import CommercialRuntime, RuntimeInvariantError


ENGINE_SHA = "d384bbbbf0b62bb0dd7d10f274cc5358939f5580a1d7c962dfa6ff59ad0b124d"
PILOT = OfferPolicy(
    code="pilot",
    amount_minor=490000,
    currency="BRL",
    product_code="Lastro Check",
    require_license_before_fulfillment=False,
    require_license_expiry=False,
)


def make_runtime():
    return CommercialRuntime(
        {"pilot": PILOT},
        EvidencePaymentVerifier(),
        EvidenceLicenseVerifier(),
        InMemoryPaymentReferenceStore(),
    )


def ready_order(order_id="ord", customer="Acme", project="Project A"):
    runtime = make_runtime()
    order = OrderRecord(order_id, "pilot", PILOT.product_code, customer, project, PILOT.amount_minor, PILOT.currency)
    runtime.qualify(order)
    runtime.request_payment(order)
    runtime.confirm_payment(
        order,
        PaymentEvidence(
            "provider",
            f"payment-{order_id}",
            PILOT.amount_minor,
            PILOT.currency,
            "2026-09-08T12:00:00Z",
            True,
        ),
    )
    runtime.authorize_fulfillment(order)
    return runtime, order


def build_bundle(root: Path, order):
    report = root / "report.json"
    provenance = root / "provenance.json"
    report.write_text("{}", encoding="utf-8")
    source = root / "source.csv"
    source.write_text("id,amount\n1,10\n", encoding="utf-8")
    write_provenance_manifest(provenance_manifest(engine_version="0.1.1", sources=[source_ref_for_file(source, locator="row 2", adapter="csv", adapter_version="0.1.1")], outputs=[report]), provenance)
    refs = collect_artifacts([report, provenance], base_dir=root)
    receipt = build_receipt(
        order,
        refs,
        engine_version="0.1.1",
        engine_distribution_sha256=ENGINE_SHA,
        provenance_artifact_path="provenance.json",
    )
    return report, provenance, receipt


class DistributionFulfillmentTests(unittest.TestCase):
    def test_private_key_marker_is_rejected(self):
        marker = b"-----BEGIN " + b"PRIVATE KEY-----"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "bad.bin").write_bytes(marker + b"\nabc")
            with self.assertRaises(UnsafeDistributionError):
                assert_distribution_safe(root)

    def test_sensitive_filenames_include_env_variants(self):
        for filename in (
            ".env",
            ".env.production",
            "credentials.json",
            "credentials.prod.json",
            "signing-key.txt",
            "bundle.p12",
            "client_secret.json",
        ):
            with self.subTest(filename=filename), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                (root / filename).write_text("x", encoding="utf-8")
                with self.assertRaises(UnsafeDistributionError):
                    assert_distribution_safe(root)

    def test_distribution_inspection_error_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "readme.txt"
            target.write_text("safe", encoding="utf-8")
            with mock.patch(
                "lastro.runtime.distribution._contains_private_key_marker",
                side_effect=OSError("read failure"),
            ):
                findings = scan_distribution(root)
            self.assertTrue(any("could not be inspected" in item.reason for item in findings))

    def test_runtime_package_does_not_self_flag(self):
        base = Path(__file__).resolve().parents[1]
        package_root = base / "candidate" / "lastro"
        if not package_root.exists():
            package_root = base / "lastro"
        assert_distribution_safe(package_root)

    def test_receipt_detects_artifact_tamper_and_size_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, order = ready_order()
            report, _, receipt = build_bundle(root, order)
            receipt_path = write_receipt(receipt, root / "receipt.json")
            self.assertEqual(verify_receipt(receipt_path), [])
            report.write_text("tampered-data", encoding="utf-8")
            errors = verify_receipt(receipt_path)
            self.assertTrue(any("hash mismatch" in item for item in errors))
            self.assertTrue(any("size mismatch" in item for item in errors))

    def test_receipt_is_bound_to_exact_order_and_engine(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, order_a = ready_order("ord-a", "Customer A", "Project A")
            _, _, receipt = build_bundle(root, order_a)
            receipt_path = write_receipt(receipt, root / "receipt.json")

            _, order_b = ready_order("ord-b", "Customer B", "Project B")
            errors = verify_receipt_for_order(
                receipt_path,
                order_b,
                expected_engine_version="0.1.1",
                expected_engine_distribution_sha256=ENGINE_SHA,
            )
            self.assertTrue(any("order_id" in item for item in errors))
            self.assertTrue(any("customer" in item for item in errors))
            self.assertTrue(any("project" in item for item in errors))

            runtime_b = make_runtime()
            with self.assertRaises(RuntimeInvariantError):
                runtime_b.mark_fulfilled(
                    order_b,
                    str(receipt_path),
                    expected_engine_version="0.1.1",
                    expected_engine_distribution_sha256=ENGINE_SHA,
                )

    def test_receipt_missing_order_or_offer_claim_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, order = ready_order()
            _, _, receipt = build_bundle(root, order)
            for mutation in ("missing_order", "missing_order_id", "missing_offer"):
                candidate = json.loads(json.dumps(receipt))
                if mutation == "missing_order":
                    candidate.pop("order")
                elif mutation == "missing_order_id":
                    candidate["order"].pop("order_id")
                else:
                    candidate["order"].pop("offer_code")
                path = root / f"{mutation}.json"
                path.write_text(json.dumps(candidate), encoding="utf-8")
                with self.subTest(mutation=mutation):
                    self.assertTrue(verify_receipt(path))

    def test_receipt_requires_nonempty_artifacts_and_provenance_binding(self):
        _, order = ready_order()
        with self.assertRaises(ValueError):
            build_receipt(
                order,
                [],
                engine_version="0.1.1",
                engine_distribution_sha256=ENGINE_SHA,
                provenance_artifact_path="provenance.json",
            )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = root / "report.json"
            report.write_text("{}", encoding="utf-8")
            refs = collect_artifacts([report], base_dir=root)
            with self.assertRaises(ValueError):
                build_receipt(
                    order,
                    refs,
                    engine_version="0.1.1",
                    engine_distribution_sha256=ENGINE_SHA,
                    provenance_artifact_path="provenance.json",
                )

    def test_receipt_provenance_hash_is_chained_to_delivered_artifact(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, order = ready_order()
            _, _, receipt = build_bundle(root, order)
            receipt["provenance"]["sha256"] = "0" * 64
            path = root / "receipt.json"
            path.write_text(json.dumps(receipt), encoding="utf-8")
            self.assertTrue(any("provenance hash" in item for item in verify_receipt(path)))

    def test_receipt_rejects_path_traversal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, order = ready_order()
            _, _, receipt = build_bundle(root, order)
            receipt["artifacts"][0]["path"] = "../outside.txt"
            path = root / "receipt.json"
            path.write_text(json.dumps(receipt), encoding="utf-8")
            self.assertTrue(any("unsafe artifact path" in item for item in verify_receipt(path)))

    def test_mark_fulfilled_requires_verified_receipt_for_same_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            runtime, order = ready_order("ord-mark")
            _, _, receipt = build_bundle(root, order)
            receipt_path = write_receipt(receipt, root / "receipt.json")
            runtime.mark_fulfilled(
                order,
                str(receipt_path),
                expected_engine_version="0.1.1",
                expected_engine_distribution_sha256=ENGINE_SHA,
            )
            self.assertEqual(order.state.value, "fulfilled")

    def test_receipt_engine_identity_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, order = ready_order()
            _, _, receipt = build_bundle(root, order)
            path = write_receipt(receipt, root / "receipt.json")
            errors = verify_receipt_for_order(
                path,
                order,
                expected_engine_version="9.9.9",
                expected_engine_distribution_sha256="1" * 64,
            )
            self.assertIn("engine version mismatch", errors)
            self.assertIn("engine distribution SHA-256 mismatch", errors)


if __name__ == "__main__":
    unittest.main()
