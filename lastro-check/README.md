# Lastro Check v0.1.3

**Lastro Check is LASTRO's domain-agnostic verification mechanism.** It is designed to test operational claims against independent evidence and explicit verification rules, then preserve a traceable verdict, provenance and evidence artifacts.

The current v0.1.2 candidate implements **two verifier modules** — Receivables and Documents — plus horizontal commercial/trust infrastructure. These implemented modules are the first concrete uses of the Lastro Check abstraction; they are **not the permanent definition of the product**.

Read `PRODUCT_SCOPE.md` and `docs/SCOPE_CONTRACT_v1.json` before using the current module layout to make product-scope decisions.

## Product-level verification contract

Conceptually:

```text
claim + independent evidence sources + verification profile/rules
    -> verification
    -> verdict + evidence + provenance + rule trace + artifacts/hashes
```

The product-level verdict vocabulary is `CONFIRMED`, `DIVERGENT`, `AMBIGUOUS`, `NOT_PROVABLE`. Current domain CLIs may expose more specific statuses for backward compatibility; v0.1.2 does not claim that every command already emits the generic vocabulary.

## Current executable verifier modules

### 1. Receivables verifier

Reconciles three independent evidence layers:

1. sales / expected receivables;
2. acquirer or payment-provider settlements;
3. actual bank postings.

It identifies missing settlements, fee mismatch, gross/net mismatch, late settlement, duplicate provider records and bank-missing events. It produces `reconciliation.csv`, `summary.json` and a portable `report.html`.

### 2. Documents verifier

Scans a folder recursively and emits auditable evidence with relative path, MIME type, size, UTC modification timestamp, SHA-256 and duplicate grouping.

Outputs: `manifest.csv`, `manifest.json`, `duplicates.json`.

## Horizontal commercial / trust infrastructure

### Signed licensing

Uses Ed25519 signatures. **The licensor private key is never part of a distributable package.** A deployed client receives only the public key needed for verification. Licenses can bind customer, product, expiry, seats and feature flags.

The repository also contains shared provenance/output hashing, bounded matching/ambiguity controls, payment/order binding, fulfillment receipts and distribution preflight. These capabilities surround verifier modules; they do not define a verifier domain.

## Install and verify

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e . pytest
pytest -q
```

## Demo — current verifier modules

```bash
lastro reconcile --sales examples/sales.csv --acquirer examples/acquirer.csv --bank examples/bank.csv --out demo-output
lastro inventory --root examples --out inventory-output
```

## Licensor-only setup

Generate signing material **outside the source/distribution directory**:

```bash
mkdir -p ../lastro-licensor-secrets
lastro license-keygen \
  --private ../lastro-licensor-secrets/licensor-private.pem \
  --public ../lastro-licensor-secrets/licensor-public.pem
```

Keep `licensor-private.pem` offline/private. On POSIX systems Lastro writes it with owner-only permissions (`0600`). Do not commit, zip, upload or send it to customers.

Issue a license from the licensor environment:

```bash
lastro license-issue \
  --private ../lastro-licensor-secrets/licensor-private.pem \
  --license customer.license.json \
  --customer "Pilot Customer" \
  --expires 2026-12-31 \
  --seats 5 \
  --feature reconciliation \
  --feature document_inventory
```

Customer verification needs only the public key:

```bash
lastro license-verify \
  --public licensor-public.pem \
  --license customer.license.json
```

## Current implementation boundary

This release candidate is deliberately bounded. v0.1.2 does **not currently implement** municipal ERP/SIAFIC, a web/mobile asset-management UI, RFID collection, a payment gateway, physical document custody/digitization, regulated registries, or the future verifier modules listed in `PRODUCT_SCOPE.md` unless separately implemented and verified.

That is an implementation boundary, not a permanent product-scope boundary.

## Security / privacy

- No customer data is required to leave the machine for CLI workflows.
- Document hashing uses SHA-256.
- Distributed license verification requires only a public key.
- The source distribution contains **no private signing key**.
- Outputs contain source data plus derived verifier fields.

## Status

v0.1.2 — integrated pilot candidate; production approval is separate. The historical v0.1.1 release and this v0.1.2 tree are compatibility baselines, **not conceptual ceilings**. Production deployments should add organization-specific access control, key management, audit logging, retention rules and integration adapters as required.

## Integração canônica v0.1.2

Derivado do ZIP original v0.1.1 com SHA-256
`d384bbbbf0b62bb0dd7d10f274cc5358939f5580a1d7c962dfa6ff59ad0b124d`.
As camadas de confiabilidade e runtime agora usam o namespace real `lastro`.

- O verifier de Receivables usa candidatos bancários que respeitam valor e janela de datas (`--bank-date-window-days`, padrão 3), inclusive com referência exata. Empates ficam como `BANK_AMBIGUOUS`, sem escolher arbitrariamente um lançamento; `match_method` distingue referência exata e heurística limitada.
- Os verificadores atuais geram `provenance.json` com hashes das fontes e saídas. Diretórios de saída existentes são recusados para preservar evidência anterior.
- CSV neutraliza fórmulas em campos textuais. Valores monetários conservam seu tipo lógico.
- `python -m lastro.license_guard` verifica assinatura e identidade nomeada e emite claims e hash compatíveis com `ExternalCommandLicenseVerifier`. O prefixo do comando deve terminar em `--license`; o adapter acrescenta o caminho.
- `python scripts/build_distribution.py --out ../release-nova` cria ZIP e wheel usando uma área isolada, lista explícita de arquivos e inspeção antes de empacotar. A pasta de saída precisa ser nova. O wheel também é inspecionado descompactado.

Os verifier CLIs continuam independentes do controle comercial. O integrador deve usar o runtime/guard antes de autorizar uma execução contratada; isso não constitui DRM, revogação remota ou validação de pagamento bancário. Os adapters de evidência são interfaces para um verificador confiável, não prova autônoma de recebimento.

Os testes e a documentação de revisão ficam no repositório. O ZIP cliente inclui engine, exemplos sintéticos, README, metadados e scripts; não inclui testes nem registros comerciais. Rode `pytest` a partir do checkout de desenvolvimento.


## Release v0.1.3 — validade das entradas e entrega comercial

A v0.1.3 preserva os módulos atuais e a constituição de escopo. Valores monetários
vazios/não finitos, CSV malformado, IDs de venda repetidos e prazos negativos são
recusados. Ausência de valor não é zero, e uma entrada inválida não gera confirmação.
O pacote cliente agora contém PRODUCT_SCOPE.md e os contratos/guias em docs/.
Leia docs/CLIENT_GUIDE.md para instalação, avaliação, interpretação e suporte.
