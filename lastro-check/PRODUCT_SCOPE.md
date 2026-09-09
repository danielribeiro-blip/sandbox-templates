# LASTRO / Lastro Check — Product Scope Constitution v1

Effective: 09/09/2026 BRT

This document corrects a real scope drift that occurred when the first executable MVP became treated as the product definition.

## 1. LASTRO definition

**LASTRO is independent verification and evidence infrastructure.**

It exists to confront what systems, documents, people or processes claim happened with the available independent evidence and verification rules, and to preserve a reproducible evidence trail.

The core question is:

> **A claim says X happened. Do the available independent sources support X, contradict X, leave X ambiguous, or fail to prove X?**

LASTRO does not need to execute the primary operation being verified. Its role is to verify, explain and preserve evidence about that operation.

## 2. Lastro Check definition

**Lastro Check is LASTRO's domain-agnostic verification mechanism.**

The product-level abstraction is:

```text
claim + independent evidence sources + verification profile/rules
    -> verification
    -> verdict + evidence + provenance + rule trace + artifacts/hashes
```

The canonical product-level verdict vocabulary is:

- `CONFIRMED`
- `DIVERGENT`
- `AMBIGUOUS`
- `NOT_PROVABLE`

This vocabulary is the architectural contract. Current domain modules may still expose more specific legacy statuses; they must not be misread as the only possible Lastro Check semantics.

## 3. Current v0.1.2 implementation

The integrated v0.1.2 candidate currently materializes **two verifier modules**:

1. **Receivables verifier** — expected/sales -> acquirer/provider -> bank evidence.
2. **Documents verifier** — recursive inventory, SHA-256, metadata and duplicate evidence.

These are the first implemented verification profiles. They are **not** the definition or conceptual ceiling of Lastro Check.

The following are horizontal infrastructure shared by verifier modules and are also not product-domain definitions:

- provenance and source/output hashing;
- matching primitives and bounded ambiguity handling;
- signed commercial licensing;
- payment binding and order state;
- fulfillment receipts;
- distribution preflight and secret/private-key blocking;
- audit trail and reproducible evidence artifacts.

## 4. Compatibility baseline versus scope authority

Historical `lastro-commercial-v0.1.1.zip` and the integrated v0.1.2 tree are **executable compatibility baselines**.

They establish behavior that must not be silently regressed, especially around:

- receivables reconciliation;
- document inventory;
- hashes and provenance;
- licensing and distribution security;
- runtime trust-boundary hardening.

They do **not** define the permanent product boundary.

Therefore:

> **Preserve implemented behavior; do not preserve accidental conceptual narrowing.**

## 5. Extension model

New verifier modules may be added without redefining LASTRO or Lastro Check. Examples include:

- billing;
- inventory/stock;
- contracts;
- deliveries;
- commissions;
- service performance;
- documentary compliance.

The abstraction remains the same: a claim is tested against independent evidence and explicit rules, producing a traceable verdict.

## 6. Non-regression rules for repository work

A change must not:

1. define `LASTRO` as receivables reconciliation;
2. define `Lastro Check` as only receivables reconciliation plus document inventory;
3. call the v0.1.1/v0.1.2 domain mix the permanent product core;
4. treat `reconcile.py` as the identity of Lastro Check rather than the current Receivables verifier;
5. treat `inventory.py` as the full document/product scope rather than the current Documents verifier;
6. duplicate a second product core when a new verifier profile/module is enough;
7. remove or weaken horizontal hardening merely because the product scope is broader.

## 7. Architectural migration principle

The current executable behavior should be preserved while the generic verification contract is extracted incrementally.

Do not perform a destructive rewrite merely to make the code look generic.

Preferred direction:

```text
Lastro Check verification kernel
    + verifier profile: receivables
    + verifier profile: documents
    + future verifier profiles
    + shared evidence/provenance/runtime infrastructure
```

The generic kernel may evolve in a later release. Scope restoration itself does not invalidate the v0.1.2 candidate or require rewriting the validated domain algorithms before they can be independently audited.

## 8. Commercial language rule

Correct:

> Lastro Check currently includes receivables and document verification modules.

Incorrect:

> Lastro Check is a receivables reconciliation and document-inventory product.

Correct LASTRO shorthand:

> **You say X happened. LASTRO checks whether independent evidence supports it and leaves the proof organized.**
