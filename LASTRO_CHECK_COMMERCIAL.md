# Lastro Check v0.1.1 — Paid Technical Pilot & Component Licensing

Lastro Check is a bounded software component for organizations that need auditable reconciliation and document-control evidence without replacing their existing ERP, DMS or operational platform.

## Paid pilot — R$ 4.900

A fixed-scope technical pilot can cover one of the following:

- **Document inventory:** recursive manifest, SHA-256 hashing, MIME/size/timestamp capture, duplicate grouping and exportable audit evidence.
- **Receivables reconciliation:** three-layer comparison of expected sales, acquirer records and bank settlement, with exception flags and quantified financial gaps.
- **Combined pilot:** both engines on a defined sample when the dataset is small enough to remain inside the fixed pilot scope.

### Deliverables

1. executed analysis on the authorized sample;
2. structured CSV/JSON/HTML outputs where applicable;
3. exception and duplicate report;
4. technical handoff memo with findings, limitations and recommended integration points;
5. commercial proposal for component licensing if the pilot validates fit.

## Component license / integration

Lastro Check may be licensed as a software component to integrators, BPO providers, document-management companies, accounting/finance teams and public-sector solution providers that already own the surrounding workflow.

Typical integration targets:

- document inventory and migration control;
- evidence-quality file manifests;
- duplicate detection before digitization or archival migration;
- settlement and receivables exception detection;
- reconciliation evidence used by a larger ERP, DMS, asset-management or back-office solution.

Commercial licensing is negotiated per deployment, expected volume, support burden, redistribution rights and source-code requirements.

## What Lastro Check does not claim to be

Current v0.1.1 is an engine/CLI component. It is **not** a complete ERP, municipal asset-management suite, RFID platform, physical document custody service, industrial scanning operation, or web/mobile end-user system.

## Security

Commercial distribution starts at **v0.1.1**. An earlier internal package was revoked after a distribution-key exposure was detected during audit. v0.1.1 removes private signing material from the distributable and includes automated distribution-security checks.

## Start a paid pilot or licensing discussion

Open a GitHub issue in this repository with:

- `LASTRO PILOT` or `LASTRO LICENSE` in the title;
- use case;
- approximate record/file volume;
- desired output;
- target delivery date;
- whether source-code, redistribution or private deployment rights are required.

A bounded pilot is priced at **R$ 4.900**. No customer data should be posted publicly; describe only the scope in the issue and keep any dataset in an authorized private transfer channel.
