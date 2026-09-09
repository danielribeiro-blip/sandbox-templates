"""Integration regressions against the recovered core, not overlay stubs."""
import csv
import hashlib
import json
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

from lastro import __version__
from lastro.licensing import generate_keypair, issue_license
from lastro.license_guard import check
from lastro.reconcile import read_csv, reconcile, write_reconciliation
from lastro.runtime.adapters import ExternalCommandLicenseVerifier
from lastro.runtime.domain import LicenseEvidence, OfferPolicy, OrderRecord
from lastro.runtime.fulfillment import build_receipt, collect_artifacts, verify_receipt, write_receipt
from scripts.build_distribution import stage_source
from test_integrated_distribution_fulfillment import ready_order

ROOT = Path(__file__).resolve().parents[1]


def inputs():
    return tuple(read_csv(ROOT / 'examples' / f'{name}.csv') for name in ('sales', 'acquirer', 'bank'))


def test_actual_matcher_rejects_distant_exact_and_ambiguous_matches():
    sales, acq, bank = inputs()
    distant = dict(bank[0], posting_date='2027-01-01')
    rows, _ = reconcile(sales[:1], acq[:1], [distant])
    assert 'BANK_MISSING' in rows[0].exceptions
    rows, _ = reconcile(sales[:1], acq[:1], [bank[0], dict(bank[0])])
    assert 'BANK_AMBIGUOUS' in rows[0].exceptions
    assert rows[0].match_method == 'AMBIGUOUS'
    rows, _ = reconcile(sales[:1], acq[:1], [dict(bank[0], reference='')])
    assert rows[0].match_method == 'BOUNDED_HEURISTIC'


def test_actual_csv_writer_neutralizes_identifier_without_changing_money(tmp_path):
    sales, acq, bank = inputs()
    sales[0]['transaction_id'] = acq[0]['transaction_id'] = '=SUM(1,2)'
    rows, _ = reconcile(sales, acq, bank)
    path = tmp_path / 'report.csv'
    write_reconciliation(rows, path)
    with path.open(newline='', encoding='utf-8') as f:
        first = next(csv.DictReader(f))
    assert first['transaction_id'].startswith("'=")
    assert first['gross_expected'] == '1000.00'
    with pytest.raises(FileExistsError):
        write_reconciliation(rows, path)


def test_real_cli_provenance_receipt_and_tampering(tmp_path):
    out = tmp_path / 'run'
    command = [sys.executable, '-m', 'lastro.cli', 'reconcile']
    for name in ('sales', 'acquirer', 'bank'):
        command += ['--' + name, str(ROOT / 'examples' / (name + '.csv'))]
    command += ['--out', str(out)]
    subprocess.run(command, check=True, capture_output=True)
    provenance = json.loads((out / 'provenance.json').read_text())
    assert provenance['engine_version'] == __version__
    assert len(provenance['sources']) == 3
    for source in provenance['sources']:
        assert source['source_sha256'] == hashlib.sha256((ROOT / 'examples' / source['source_name']).read_bytes()).hexdigest()
    runtime, order = ready_order('synthetic-e2e')
    receipt = build_receipt(order, collect_artifacts(list(out.iterdir()), base_dir=out), engine_version=__version__, engine_distribution_sha256='a'*64, provenance_artifact_path='provenance.json')
    receipt_path = write_receipt(receipt, out / 'receipt.json')
    assert verify_receipt(receipt_path) == []
    runtime.mark_fulfilled(order, str(receipt_path), expected_engine_version=__version__, expected_engine_distribution_sha256='a'*64)
    (out / 'reconciliation.csv').write_text('tampered')
    assert verify_receipt(receipt_path)
    assert subprocess.run(command, capture_output=True).returncode != 0


def test_real_inventory_has_matching_source_and_output_hashes(tmp_path):
    source = tmp_path / 'input'; source.mkdir()
    (source / '=formula.txt').write_text('same bytes')
    (source / 'copy.txt').write_text('same bytes')
    out = tmp_path / 'inventory'
    subprocess.run([sys.executable, '-m', 'lastro.cli', 'inventory', '--root', str(source), '--out', str(out)], check=True, capture_output=True)
    manifest = json.loads((out / 'provenance.json').read_text())
    assert len(manifest['sources']) == 2
    assert len({row['source_sha256'] for row in manifest['sources']}) == 1
    assert json.loads((out / 'manifest.json').read_text())['summary']['duplicate_groups'] == 1
    for artifact in manifest['outputs']:
        assert artifact['sha256'] == hashlib.sha256((out / artifact['file']).read_bytes()).hexdigest()


def test_signed_guard_connects_to_runtime_and_rejects_tampering(tmp_path):
    private, public, license_file = [tmp_path / n for n in ('private.pem', 'public.pem', 'license.json')]
    generate_keypair(private, public)
    identity = {'licensee':'Integrator', 'named_customer':'Acme', 'named_project':'Project A', 'order_id':'ord-license'}
    issue_license(private, license_file, customer=json.dumps(identity), product='Lastro Check', expires=(date.today()+timedelta(days=30)).isoformat(), seats=1, features=['reconciliation'])
    args = dict(licensee='Integrator', customer='Acme', project='Project A', order='ord-license', feature='reconciliation')
    claims = check(public, license_file, **args)['claims']
    evidence = LicenseEvidence(**claims, verified=True)
    policy = OfferPolicy('license',2490000,'BRL','Lastro Check',True)
    order = OrderRecord('ord-license','license','Lastro Check','Acme','Project A',2490000,'BRL')
    command = [sys.executable,'-m','lastro.license_guard','--public',str(public)]
    for key, value in args.items():
        command += ['--'+key, value]
    verifier = ExternalCommandLicenseVerifier(command + ['--license'], license_file)
    assert verifier.verify(order, policy, evidence)
    with pytest.raises(ValueError):
        check(public, license_file, **dict(args, project='another project'))
    obj = json.loads(license_file.read_text()); obj['payload']['expires'] = '2099-01-01'
    license_file.write_text(json.dumps(obj))
    assert not verifier.verify(order, policy, evidence)


def test_builder_preflight_blocks_secrets_in_selected_package(tmp_path):
    stage = tmp_path / 'clean'
    stage_source(ROOT, stage)
    (stage / 'lastro' / 'credentials.json').write_text('{"synthetic":"fixture"}')
    from lastro.runtime.distribution import UnsafeDistributionError
    with pytest.raises(UnsafeDistributionError):
        stage_source(stage, tmp_path / 'rejected')
