"""Fail-closed preflight for v0.1.1 licenses. Not DRM or revocation service."""
import argparse
import json
import sys
import hashlib
from pathlib import Path
from datetime import date, datetime, time, timedelta, timezone
from lastro.licensing import verify_license_bytes


def check(public, license_file, *, licensee, customer, project, order, feature, today=None):
    raw = Path(license_file).read_bytes()
    brt = timezone(timedelta(hours=-3))
    result = verify_license_bytes(public, raw, today=today or datetime.now(brt).date())
    if result['expired']:
        raise ValueError('license expired')
    payload = result['payload']
    if payload.get('product') != 'Lastro Check':
        raise ValueError('wrong product')
    if type(payload.get('seats')) is not int or payload['seats'] < 1:
        raise ValueError('invalid seats')
    if feature not in {'reconciliation', 'document_inventory'} or feature not in payload.get('features', []):
        raise ValueError('feature not licensed')
    expected = {'licensee': licensee, 'named_customer': customer, 'named_project': project, 'order_id': order}
    if not all(isinstance(v, str) and v.strip() for v in expected.values()):
        raise ValueError('empty expected identity')
    if json.loads(payload['customer']) != expected:
        raise ValueError('named identity mismatch')
    expiry = datetime.combine(date.fromisoformat(payload['expires']) + timedelta(days=1), time.min, brt).isoformat()
    return {'authorized': True, 'order_id': order, 'expires': payload['expires'], 'feature': feature,
            'verified': True, 'license_sha256': hashlib.sha256(raw).hexdigest(),
            'claims': {'reference': order, 'product': payload['product'], 'customer': customer,
                       'project': project, 'expires_at': expiry}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for field in ('public', 'license', 'licensee', 'customer', 'project', 'order', 'feature'):
        parser.add_argument('--'+field, required=True)
    args = vars(parser.parse_args())
    args['license_file'] = args.pop('license')
    try:
        print(json.dumps(check(**args), ensure_ascii=False))
    except Exception as exc:
        print(json.dumps({'authorized': False, 'error': type(exc).__name__}), file=sys.stderr)
        return 2
    return 0

if __name__ == '__main__':
    sys.exit(main())
