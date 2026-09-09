import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

from lastro_check.runtime.adapters import EvidenceLicenseVerifier, EvidencePaymentVerifier, ExternalCommandLicenseVerifier, ExternalCommandPaymentVerifier, InMemoryPaymentReferenceStore
from lastro_check.runtime.distribution import UnsafeDistributionError, assert_distribution_safe
from lastro_check.runtime.domain import LicenseEvidence, OfferPolicy, OrderRecord, PaymentEvidence
from lastro_check.runtime.fulfillment import MINIMUM_SUPPORTED_ENGINE_VERSION, build_receipt, collect_artifacts, verify_receipt, verify_receipt_for_order, write_receipt
from lastro_check.runtime.service import CommercialRuntime

ENGINE_SHA = "d384bbbbf0b62bb0dd7d10f274cc5358939f5580a1d7c962dfa6ff59ad0b124d"
PILOT = OfferPolicy("pilot", 490000, "BRL", "Lastro Check", False, False, False)
LICENSE = OfferPolicy("license", 2490000, "BRL", "Lastro Check", True, True, True)


def make_order(policy=PILOT, order_id="ord-v3"):
    return OrderRecord(order_id, policy.code, policy.product_code, "Acme", "Project A", policy.amount_minor, policy.currency)


def valid_payment(order, ref="pay-v3"):
    return PaymentEvidence("provider", ref, order.amount_minor, order.currency, "2026-09-08T12:00:00Z", True)


def ready_order(order_id="ord-v3"):
    runtime = CommercialRuntime({"pilot": PILOT}, EvidencePaymentVerifier(), EvidenceLicenseVerifier(), InMemoryPaymentReferenceStore())
    order = make_order(PILOT, order_id)
    runtime.qualify(order); runtime.request_payment(order); runtime.confirm_payment(order, valid_payment(order, f"pay-{order_id}")); runtime.authorize_fulfillment(order)
    return runtime, order


def valid_bundle(root: Path, order, engine_version="0.1.1"):
    report = root / "report.json"; report.write_text('{"ok":true}', encoding="utf-8")
    report_sha = hashlib.sha256(report.read_bytes()).hexdigest()
    provenance = root / "provenance.json"
    provenance.write_text(json.dumps({"schema":"lastro.check.provenance.v1","engine_version":engine_version,"sources":[{"source_name":"input.csv","source_sha256":"b"*64,"locator":"row:2","adapter":"csv","adapter_version":"1","identity_quality":"SOURCE_PROVIDED"}],"outputs":[{"file":"report.json","bytes":report.stat().st_size,"sha256":report_sha}]}), encoding="utf-8")
    refs = collect_artifacts([report, provenance], base_dir=root)
    return report, provenance, build_receipt(order, refs, engine_version=engine_version, engine_distribution_sha256=ENGINE_SHA, provenance_artifact_path="provenance.json")


class AuditFixV3Tests(unittest.TestCase):
    def _script(self, root: Path, name: str, payload: dict, sleep=0):
        path = root / name
        path.write_text((f"import time\ntime.sleep({sleep})\n" if sleep else "") + "import json\n" + f"print(json.dumps({payload!r}))\n", encoding="utf-8")
        return path

    def test_payment_verified_string_false_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); event=root/"event"; event.write_text("event"); order=make_order(); evidence=valid_payment(order)
            payload={"verified":"false","event_sha256":hashlib.sha256(event.read_bytes()).hexdigest(),"payment":{"provider":evidence.provider,"reference":evidence.reference,"amount_minor":evidence.amount_minor,"currency":evidence.currency,"confirmed_at":evidence.confirmed_at}}
            self.assertFalse(ExternalCommandPaymentVerifier([sys.executable,str(self._script(root,"p.py",payload))],event).verify(order,evidence))

    def test_license_verified_string_false_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); lic=root/"license"; lic.write_text("license"); order=make_order(LICENSE); evidence=LicenseEvidence("lic","Lastro Check","Acme","Project A","2099-01-01T00:00:00Z",True)
            payload={"verified":"false","license_sha256":hashlib.sha256(lic.read_bytes()).hexdigest(),"claims":{"reference":evidence.reference,"product":evidence.product,"customer":evidence.customer,"project":evidence.project,"expires_at":evidence.expires_at}}
            self.assertFalse(ExternalCommandLicenseVerifier([sys.executable,str(self._script(root,"l.py",payload))],lic).verify(order,LICENSE,evidence))

    def test_amount_minor_requires_json_integer(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); event=root/"event"; event.write_text("event"); order=make_order(); evidence=valid_payment(order); sha=hashlib.sha256(event.read_bytes()).hexdigest()
            for bad in (490000.9,"490000",True):
                payload={"verified":True,"event_sha256":sha,"payment":{"provider":evidence.provider,"reference":evidence.reference,"amount_minor":bad,"currency":evidence.currency,"confirmed_at":evidence.confirmed_at}}
                with self.subTest(bad=bad): self.assertFalse(ExternalCommandPaymentVerifier([sys.executable,str(self._script(root,f"p{type(bad).__name__}.py",payload))],event).verify(order,evidence))

    def test_verifier_timeout_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); event=root/"event"; event.write_text("event"); order=make_order(); evidence=valid_payment(order)
            payload={"verified":True,"event_sha256":hashlib.sha256(event.read_bytes()).hexdigest(),"payment":{"provider":evidence.provider,"reference":evidence.reference,"amount_minor":evidence.amount_minor,"currency":evidence.currency,"confirmed_at":evidence.confirmed_at}}
            self.assertFalse(ExternalCommandPaymentVerifier([sys.executable,str(self._script(root,"slow.py",payload,.2))],event,timeout_seconds=.02).verify(order,evidence))

    def test_git_metadata_and_windows_traversal_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); (root/".git").mkdir()
            with self.assertRaises(UnsafeDistributionError): assert_distribution_safe(root)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); _,order=ready_order("win"); _,_,receipt=valid_bundle(root,order); receipt["artifacts"][0]["path"]="..\\secret.txt"; path=root/"receipt.json"; path.write_text(json.dumps(receipt))
            self.assertTrue(any("unsafe artifact path" in e for e in verify_receipt(path)))

    def test_empty_provenance_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); _,order=ready_order("prov"); report,prov,receipt=valid_bundle(root,order); prov.write_text("{}")
            refs=collect_artifacts([report,prov],base_dir=root); receipt["artifacts"]=[{"path":x.path,"sha256":x.sha256,"size_bytes":x.size_bytes} for x in refs]; pref=next(x for x in receipt["artifacts"] if x["path"]=="provenance.json"); receipt["provenance"]={"artifact_path":"provenance.json","sha256":pref["sha256"]}; path=root/"receipt.json"; path.write_text(json.dumps(receipt))
            self.assertTrue(any("provenance" in e for e in verify_receipt(path)))

    def test_fulfillment_pins_receipt_sha_and_blocks_010(self):
        self.assertEqual(MINIMUM_SUPPORTED_ENGINE_VERSION,"0.1.1")
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); runtime,order=ready_order("pin"); _,_,receipt=valid_bundle(root,order); path=write_receipt(receipt,root/"receipt.json"); expected=hashlib.sha256(path.read_bytes()).hexdigest(); runtime.mark_fulfilled(order,str(path),expected_engine_version="0.1.1",expected_engine_distribution_sha256=ENGINE_SHA); self.assertEqual(order.fulfillment_receipt_sha256,expected); self.assertIn(expected,order.audit_log[-1]["reference"])
            errors=verify_receipt_for_order(path,order,expected_engine_version="0.1.0",expected_engine_distribution_sha256=ENGINE_SHA); self.assertTrue(any("minimum supported" in e for e in errors))


if __name__ == "__main__": unittest.main()
