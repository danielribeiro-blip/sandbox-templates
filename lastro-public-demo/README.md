# Lastro Check v0.1.1 — Public Document Audit Demo

This demo uses **synthetic, non-confidential files** created only to show the commercial behavior of the document-inventory engine.

## Scenario

A migration/digitization batch contains six synthetic document files spread across two boxes plus one batch-control CSV (7 files total). One document was copied without change into another box, while another was reprocessed with modified content.

## Executed result

Lastro Check scanned the folder recursively and produced an auditable manifest with relative path, MIME type, size, UTC modification timestamp, SHA-256 and duplicate grouping.

Published evidence:

- `manifest.csv` — executed engine output
- `duplicates.json` — executed engine output
- `RESULTS.md` — human-readable result summary
- `OUTPUT_SHA256.txt` — integrity hashes for published engine outputs

Exact-content duplicates are grouped by hash. Reprocessed/changed content receives a different hash and is not silently collapsed into the duplicate group.

## Commercial relevance

For document-management, digitization, archival migration and BPO operations, this creates an independent evidence layer showing exactly what entered a batch, which files are byte-identical duplicates and which files differ despite similar names.

This demo does **not** claim physical custody, scanning, OCR, GED replacement or legal evidentiary certification. It demonstrates the bounded Lastro Check v0.1.1 inventory/hash component.
