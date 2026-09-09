# LicitaGate — auditoria pré-proposta para licitações

**Antes de enviar uma proposta, transforme o edital e os documentos da empresa em uma decisão GO/NO-GO verificável.**

LicitaGate é uma entrega B2B de inteligência e conferência pré-proposta para empresas que já vendem — ou querem vender — ao poder público. O objetivo é simples: identificar, antes do envio, requisitos que podem gerar inabilitação, proposta inexequível, obrigação técnica não atendida ou contrato economicamente ruim.

## O que entra

- edital, termo de referência e anexos;
- dados públicos da contratação;
- documentos e atestados que a empresa autorizar compartilhar;
- escopo técnico e premissas comerciais da proposta.

## O que sai

1. **Matriz requisito → evidência → status → ação**;
2. **GO / NO-GO / GO CONDICIONAL**, com blockers explícitos;
3. checklist de habilitação e validade documental;
4. cobertura de atestados de capacidade técnica;
5. mapa de exigências operacionais, software, implantação, suporte e SLA;
6. prazos críticos e pontos que exigem esclarecimento/impugnação;
7. riscos de proposta, preço e obrigações contratuais identificáveis no material fornecido;
8. checklist final de submissão;
9. no pacote ampliado, estrutura de proposta técnica/comercial pronta para preenchimento e revisão.

## Regra de evidência

Cada conclusão relevante é marcada como **CONFIRMADA**, **PENDENTE**, **CONTROVERTIDA** ou **INFERIDA**. Nenhuma certidão, atestado, capacidade técnica, integração, experiência ou requisito é presumido como existente sem fonte.

## Pacotes

### Gate — R$ 2.900 por edital
Auditoria completa do edital/TR + matriz de conformidade + GO/NO-GO + checklist de submissão.

### Gate + Proposal Pack — R$ 4.900 por edital
Inclui o Gate e acrescenta estrutura técnica/comercial de proposta, matriz de resposta item a item e revisão final pré-envio.

### Operação recorrente — R$ 9.900/mês
Até 5 oportunidades qualificadas por mês, com triagem GO/NO-GO, auditoria das escolhidas e painel de blockers/próximas ações.

## Limites deliberados

LicitaGate não inventa documentação, não garante habilitação/adjudicação, não assina nem protocola propostas, não substitui engenharia/contabilidade/certificação técnica quando exigidas e não assume capacidade operacional que o fornecedor não possua. A entrega serve para tomar uma decisão melhor e reduzir erro evitável antes do compromisso externo.

## Demonstração pública

Há um preview aplicado ao Pregão Eletrônico 35/2026 do Município de Assis/SP, contratação de gestão documental com valor estimado de R$ 248.757,61 e prazo de propostas em 24/09/2026 às 09:00 BRT:

- [`sample-assis-pe35-2026.md`](sample-assis-pe35-2026.md)

O preview usa somente informações públicas verificáveis. Uma auditoria comercial completa depende do edital/anexos vigentes e da documentação autorizada da empresa.

---

**Posicionamento:** serviço de conferência e inteligência pré-proposta para fornecedores; não é plataforma genérica de busca de licitações e não exige substituir o sistema de compras, ERP ou equipe comercial do cliente.

## Produção do dossiê — versão executável

[Fundamento e diferenciais](WEDGE_AND_EXECUTION.md) · [Protocolo de entrega](DELIVERY_PROTOCOL.md)

A ferramenta local [gate.py](gate.py) transforma uma matriz previamente revisada em relatório HTML, CSV, decisão JSON e registro de hashes. Não interpreta edital automaticamente. Sem conjunto completo e revisão declarada, a decisão permanece PENDENTE.

[Demonstração sintética](examples/output/report.html) · [Entrada reproduzível](examples/synthetic-case.json)

A demonstração não representa documentos de uma empresa nem auditoria final de Assis. A execução comercial requer fontes completas, canal privado, escopo/prazo confirmados e cobrança operacional.


## Prova aplicada em fonte oficial

[Assis: 12 achados com páginas e cálculo conferido](research/ASSIS_FINDINGS_20260909.md) · [Perguntas de esclarecimento preparadas](research/ASSIS_CLARIFICATION_DRAFT.md) · [Edital oficial preservado](research/assis-edital.pdf).

Inclui divergência no prazo de pagamento, início operacional imediato, ambiguidades de medição e conferência aritmética da planilha. Nenhuma conclusão sobre habilitação de empresa nem esclarecimento protocolado.
