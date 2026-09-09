# Lastro Check — Audit Fix v3 candidate

This branch contains the direct repository correction candidate produced from the independent re-audit of Audit Fix v2. It is **not** the canonical production engine and must not be represented as a released build.

## Internal findings closed in this candidate

- external verifier `verified` is accepted only when the JSON value is exactly boolean `true`;
- external payment `amount_minor` requires an actual JSON integer; bool/float/string values are rejected;
- payment and license verifier subprocesses have fail-closed timeouts;
- `.git` metadata is rejected in client distribution staging instead of silently skipped;
- fulfillment artifact paths reject Windows separators/drives/UNC/traversal as well as POSIX traversal;
- provenance is semantically validated as `lastro.check.provenance.v1` and its outputs are bound to delivered artifact hashes;
- the fulfillment receipt SHA-256 is persisted in the order and audit transition reference;
- release evidence below Lastro Check v0.1.1 is rejected by the candidate runtime.

## Independent local validation before commit

- `python -m compileall -q lastro_check tests` — PASS
- `python -m pytest -q` — 51 passed + 26 subtests
- `python -m unittest discover -s tests -v` — 51 passed

## Remaining production gate

Production remains **NOT APPROVED** until the canonical Lastro Check engine source tree, real client release builder and real signed-license guard are materialized. At that point the fixes must be merged by responsibility, wired into the real matcher/builder/guard, followed by historical core tests and demos, a clean client build/install/smoke, a new final distribution SHA-256, and independent production re-audit.
