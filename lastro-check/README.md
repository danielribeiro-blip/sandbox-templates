# Lastro Check v0.1.2

A licensable operational core for **receivables reconciliation**, **document inventory** and **offline commercial code licensing**.

## Three executable surfaces

### 1. Receivables reconciliation
Reconciles three independent evidence layers:

1. sales / expected receivables;
2. acquirer or payment-provider settlements;
3. actual bank postings.

It identifies missing settlements, fee mismatch, gross/net mismatch, late settlement, duplicate provider records and bank-missing events. It produces `reconciliation.csv`, `summary.json` and a portable `report.html`.

### 2. Document inventory
Scans a folder recursively and emits an auditable inventory with relative path, MIME type, size, UTC modification timestamp, SHA-256 and duplicate grouping.

Outputs: `manifest.csv`, `manifest.json`, `duplicates.json`.

### 3. Commercial licensing
Uses Ed25519 signatures. **The licensor private key is never part of a distributable package.** A deployed client receives only the public key needed for verification. Licenses can bind customer, product, expiry, seats and feature flags.

## Install and verify

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e . pytest
pytest -q
```

## Demo — reconciliation and inventory

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

## Commercial boundary

This package is deliberately bounded. It is an embeddable/licensable engine and **does not currently provide** a municipal ERP/SIAFIC, web/mobile asset-management UI, RFID collection layer, payment gateway, physical document custody/digitization operation or regulated registry. Those capabilities must not be claimed in a bid unless separately implemented and verified.

## Security / privacy

- No customer data is required to leave the machine for CLI workflows.
- Document hashing uses SHA-256.
- Distributed license verification requires only a public key.
- The source distribution contains **no private signing key**.
- Outputs contain source data plus derived reconciliation/inventory fields.

## Status

v0.1.2 — integrated pilot candidate; production approval is separate. Production deployments should add organization-specific access control, key management, audit logging, retention rules and integration adapters.


## Integração canônica v0.1.2

Derivado do ZIP original v0.1.1 com SHA-256
`d384bbbbf0b62bb0dd7d10f274cc5358939f5580a1d7c962dfa6ff59ad0b124d`.
As camadas de confiabilidade e runtime agora usam o namespace real `lastro`.

- Reconciliação: candidatos bancários precisam respeitar valor e janela de datas
  (`--bank-date-window-days`, padrão 3), inclusive com referência exata.
  Empates ficam como `BANK_AMBIGUOUS`, sem escolher arbitrariamente um lançamento.
  `match_method` distingue referência exata e heurística limitada.
- Ambos os motores geram `provenance.json` com hashes das fontes e saídas.
  Diretórios de saída existentes são recusados para preservar evidência anterior.
- CSV neutraliza fórmulas em campos textuais. Valores monetários conservam seu tipo lógico.
- `python -m lastro.license_guard` verifica assinatura e identidade nomeada e emite
  claims e hash compatíveis com `ExternalCommandLicenseVerifier`.
  O prefixo do comando deve terminar em `--license`; o adapter acrescenta o caminho.
- `python scripts/build_distribution.py --out ../release-nova` cria ZIP e wheel
  usando uma área isolada, lista explícita de arquivos e inspeção antes de empacotar.
  A pasta de saída precisa ser nova. O wheel também é inspecionado descompactado.

A reconciliação CLI continua independente do controle comercial. O integrador deve
usar o runtime/guard antes de autorizar uma execução contratada; isso não constitui
DRM, revogação remota ou validação de pagamento bancário. Os adapters de evidência
são interfaces para um verificador confiável, não prova autônoma de recebimento.

Os testes e a documentação de revisão ficam no repositório. O ZIP cliente inclui
engine, exemplos sintéticos, README, metadados e scripts; não inclui testes nem
registros comerciais. Rode `pytest` a partir do checkout de desenvolvimento.
