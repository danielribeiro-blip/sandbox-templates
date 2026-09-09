from __future__ import annotations

import argparse
import sys

from .distribution import UnsafeDistributionError, assert_distribution_safe
from .fulfillment import verify_receipt


def _preflight(args: argparse.Namespace) -> int:
    try:
        assert_distribution_safe(args.path)
    except (UnsafeDistributionError, FileNotFoundError, NotADirectoryError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print("distribution preflight: PASS")
    return 0


def _verify_receipt(args: argparse.Namespace) -> int:
    errors = verify_receipt(args.receipt)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 2
    print("fulfillment receipt: PASS")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="lastro-runtime")
    sub = parser.add_subparsers(required=True)

    preflight = sub.add_parser("preflight-dist")
    preflight.add_argument("path")
    preflight.set_defaults(func=_preflight)

    verify = sub.add_parser("verify-receipt")
    verify.add_argument("receipt")
    verify.set_defaults(func=_verify_receipt)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
