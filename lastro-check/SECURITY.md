# Security notes — Lastro Check v0.1.1

## Signing-key rule

The Ed25519 private licensing key is a licensor secret and must never be included in source archives, client packages, public repositories, demos or support bundles.

Version 0.1.1 removes signing material that was inadvertently bundled in v0.1.0. Any key present in a copy of v0.1.0 must be treated as compromised and must not be used for commercial licenses.

## Distribution rule

A customer distribution may contain source code, documentation, examples, tests, public verification keys and customer-specific signed license files. It must not contain a PEM private key or any other signing secret.
