# LASTRO CHECK - PRE-REAUDIT REPORT v2

**Data:** 08/09/2026 BRT  
**Objeto:** Audit Fix Overlay v2  
**Natureza:** revalidação do lado da implementação; não substitui auditoria independente.

## Resultado

A auditoria fornecida foi tratada como fonte de defeitos e os P0-01/P0-02/P0-03 foram reproduzidos diretamente contra o Harmonized Overlay v1 antes da correção:

- receipt do pedido A foi aceito para cumprir pedido B;
- ordem de licença de 1 USD avançou até `READY_FOR_FULFILLMENT`;
- licença com produto incorreto e expirada também avançou até `READY_FOR_FULFILLMENT`.

No candidato v2, esses comportamentos foram convertidos em regressões adversariais e passaram a ser rejeitados.

## Validação do candidato

- `pytest -q`: 41 PASS + 23 subtests;
- `unittest`: 41 PASS;
- `compileall`: PASS;
- distribution preflight: PASS;
- audit-fix delta patch: `git apply --check` PASS + árvore aplicada PASS;
- full v2 patch: `git apply --check` PASS + árvore aplicada PASS.

## Gate

O candidato v2 está **READY FOR CANONICAL MERGE AND INDEPENDENT REAUDIT**, mas o release produtivo permanece **FAIL** porque a árvore canônica do engine, o builder real e o guard real não estão materializados nos materiais disponíveis.

A aprovação produtiva exige merge real, suíte histórica + nova, demos inventory/reconciliation, guard machine-readable real, builder real com preflight, clean build/install/smoke e novo SHA-256 final.
