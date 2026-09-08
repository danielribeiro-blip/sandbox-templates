# Executed Results — Lastro Check v0.1.1 Public Demo

Execution timestamp (UTC): 2026-09-08T07:53:04Z

## Summary

- files scanned: **7**
- total bytes: **351**
- unique SHA-256 hashes: **6**
- duplicate groups: **1**
- files participating in duplicate groups: **2**

## Duplicate detected

`DUP-0001` contains two byte-identical files:

- `caixa_001/contrato_1001_p1.txt`
- `caixa_002/contrato_1001_p1_DUPLICADO.txt`

Both resolve to:

`68d660ba9b81498b2ed07439329234e983d5a8a6869bc71228b3f5efebd3cccc`

## Reprocessed variant correctly kept separate

`caixa_002/contrato_1001_p1_REPROCESSADO.txt` has similar naming but changed content and therefore a different SHA-256:

`e6d0fc788e0ec6da5dc3d5ff036de2c9fe59a43f43638dfd218557c836c748fd`

That distinction is the core audit behavior: duplicate names are not enough to prove duplication, and similar names do not cause changed content to be collapsed.
