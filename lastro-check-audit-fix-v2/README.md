# LASTRO CHECK - Audit Fix Overlay v2

This branch stages the independent-audit remediation candidate. It is not a production release and does not replace the canonical Lastro Check source tree.

Baseline reference: Lastro Check v0.1.1, historical distribution SHA-256 `d384bbbbf0b62bb0dd7d10f274cc5358939f5580a1d7c962dfa6ff59ad0b124d`.

Audit fixes staged here:
- receipt bound to order/product/customer/project and expected engine identity;
- offer amount/currency/product enforced by executable policy;
- license product/customer/project/expiry validation;
- machine-readable external guard contract bound to exact license-file SHA-256; exit-code-only guard rejected;
- timezone-aware payment evidence, provider/reference replay protection and SQLite idempotency boundary;
- non-empty fulfillment, provenance chaining, explicit unsigned SHA-256 integrity assurance;
- `.env*`/secret/private-key distribution gate hardening;
- integer-only matching window;
- accept/cancel operational audit metadata.

Local validation: 41 tests PASS + 23 subtests, compileall PASS, distribution preflight PASS. Delta and full patches were separately validated with `git apply --check` and fresh-tree test runs.

Production remains blocked until the canonical engine source, real builder and real signed-license guard are materialized, merged and independently re-audited.