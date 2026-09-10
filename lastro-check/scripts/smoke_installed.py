"""Run with the installed wheel's Python, from a directory outside the checkout."""
import argparse
import hashlib
import importlib.metadata
import json
import subprocess
import sys
from pathlib import Path
from lastro import __version__
from lastro.runtime.adapters import EvidenceLicenseVerifier, EvidencePaymentVerifier, InMemoryPaymentReferenceStore
from lastro.runtime.domain import OfferPolicy, OrderRecord, PaymentEvidence
from lastro.runtime.fulfillment import build_receipt, collect_artifacts, verify_receipt, write_receipt
from lastro.runtime.service import CommercialRuntime

parser = argparse.ArgumentParser()
parser.add_argument('--examples', type=Path, required=True)
parser.add_argument('--distribution', type=Path, required=True)
parser.add_argument('--out', type=Path, required=True)
a = parser.parse_args()
assert __version__ == importlib.metadata.version('lastro-check') == '0.1.3'
command = [sys.executable, '-m', 'lastro.cli', 'reconcile']
for name in ('sales', 'acquirer', 'bank'):
    command += ['--'+name, str(a.examples / (name+'.csv'))]
command += ['--out', str(a.out)]
subprocess.run(command, check=True)
summary = json.loads((a.out / 'summary.json').read_text())
assert summary['transactions'] == 4 and summary['exceptions'] == 3
policy = OfferPolicy('synthetic-demo', 490000, 'BRL', 'Lastro Check', False, require_license_expiry=False)
runtime = CommercialRuntime({policy.code:policy}, EvidencePaymentVerifier(), EvidenceLicenseVerifier(), InMemoryPaymentReferenceStore())
order = OrderRecord('SYNTHETIC-NO-PAYMENT', policy.code, policy.product_code, 'Synthetic Customer', 'Synthetic Demo', policy.amount_minor, policy.currency)
runtime.qualify(order); runtime.request_payment(order)
# Explicit synthetic fixture: this does not attest any real payment or revenue.
runtime.confirm_payment(order, PaymentEvidence('SYNTHETIC', 'NO-REAL-PAYMENT', policy.amount_minor, policy.currency, '2026-09-09T00:00:00Z', True))
runtime.authorize_fulfillment(order)
sha = hashlib.sha256(a.distribution.read_bytes()).hexdigest()
receipt = build_receipt(order, collect_artifacts(list(a.out.iterdir()), base_dir=a.out), engine_version=__version__, engine_distribution_sha256=sha, provenance_artifact_path='provenance.json')
receipt['demonstration_only'] = True
receipt_path = write_receipt(receipt, a.out / 'receipt.json')
assert verify_receipt(receipt_path) == []
runtime.mark_fulfilled(order, str(receipt_path), expected_engine_version=__version__, expected_engine_distribution_sha256=sha)
print(json.dumps({'installed_version':__version__, 'distribution_sha256':sha, 'receipt_verified':True, 'synthetic_only':True}))
