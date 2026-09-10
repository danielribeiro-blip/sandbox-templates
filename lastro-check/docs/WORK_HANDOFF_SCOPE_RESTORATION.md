# WORK HANDOFF — LASTRO Scope Restoration

Effective: 09/09/2026 BRT

## Purpose

A real product-scope drift was identified after the first Lastro Check MVP became treated as the permanent definition of the product. This handoff prevents Work from reintroducing that narrowing while continuing technical integration and production-gate work.

## What changed in the repository

No validated matching, inventory, licensing, runtime or security algorithm was removed by this correction.

The repository now carries two explicit scope authorities:

1. `lastro-check/PRODUCT_SCOPE.md` — human-readable product constitution.
2. `lastro-check/docs/SCOPE_CONTRACT_v1.json` — machine-readable scope contract.

The README and canonical-integration record were corrected so that v0.1.2 is described as the **current implementation of two verifier modules**, not as the permanent identity of Lastro Check.

A repository test validates the critical scope invariants and reading order.

## How Work must read this repo from now on

Use this authority order for product scope:

```text
1. PRODUCT_SCOPE.md
2. docs/SCOPE_CONTRACT_v1.json
3. README.md current implementation description
4. docs/CANONICAL_INTEGRATION_v0_1_2.md historical/technical integration record
5. implementation modules and tests
6. historical overlays / prior handoffs
```

Technical implementation is authoritative for what the current release **does**. It is not authoritative by itself for what LASTRO **is allowed to become**.

## Correct interpretation of the current tree

- `lastro/reconcile.py` = current **Receivables verifier implementation**, not the Lastro Check product definition.
- `lastro/inventory.py` = current **Documents verifier implementation**, not the Lastro Check product definition.
- `lastro/reconciliation/matching_policy.py` = shared matching/reliability primitive currently used by Receivables.
- `lastro/provenance.py` and output hashes = horizontal evidence infrastructure.
- `lastro/runtime/` = horizontal commercial/trust infrastructure.
- `lastro/licensing.py` / `license_guard.py` = horizontal signed-license infrastructure.
- v0.1.1 historical distribution and v0.1.2 integrated candidate = compatibility baselines, not conceptual ceilings.

## Product abstraction to preserve

```text
claim
+ independent evidence sources
+ verification profile
+ rules
      -> Lastro Check verification
      -> verdict + evidence + provenance + rule trace + artifacts/hashes
```

Product-level verdict vocabulary:

- CONFIRMED
- DIVERGENT
- AMBIGUOUS
- NOT_PROVABLE

Current module-specific statuses may remain for backward compatibility. Do not claim that every current CLI already emits the generic vocabulary.

## What Work must NOT do

Do not:

- restore README language that defines Lastro Check as a receivables/document product;
- use the phrase `core = matching + inventory + reconciliation` as a permanent product boundary;
- reject future verifier domains merely because they are absent from v0.1.2;
- build a second Lastro core for each new domain;
- remove runtime/provenance/security hardening while generalizing the product;
- rewrite validated v0.1.2 algorithms simply to satisfy the abstraction;
- treat old Commercial Runtime / audit handoffs as higher scope authority than the new scope constitution.

## What Work SHOULD do

For current production work:

1. keep the validated v0.1.2 Receivables and Documents behavior intact;
2. keep all v2/v3 trust-boundary and distribution hardening;
3. finish independent production audit against what v0.1.2 actually implements;
4. describe v0.1.2 as the first two verifier modules of a broader Lastro Check mechanism;
5. when designing the next architectural release, extract a generic verification interface/kernel incrementally and place current verifiers behind profiles/adapters without duplicating their logic.

## Scope versus production gate

The restored product scope does **not** itself certify production readiness and does **not** invalidate previous technical test evidence.

Production gate and product-scope authority are orthogonal:

- production audit asks whether the current implementation is safe, reproducible and fit for its claimed current modules;
- scope governance asks whether repository language/architecture accidentally redefines the whole product as those modules.

Both must remain true simultaneously.

## Repository branch / PR instruction

Continue from the current `lastro/canonical-integration-v012` branch and PR #3 unless a later explicit instruction creates a successor.

Do not reset to an older audit overlay branch to recover conceptual scope. The scope correction is now part of the canonical integration branch itself.

## Gate for future changes

Any change that materially redefines LASTRO or Lastro Check must be checked against `SCOPE_CONTRACT_v1.json` before merge.

If an implementation change conflicts with the scope constitution, stop and surface the conflict instead of silently narrowing the product.
