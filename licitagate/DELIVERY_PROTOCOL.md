# LicitaGate — protocolo de produção e aceite v1

09/09/2026, 01:29 BRT. Especificação operacional; não é contrato assinado.

## Entrada e prazo

Entrada: link oficial, edital, TR, todos os anexos e retificações, identificação do conjunto vigente, prazo oficial, objeto/lotes, documentos empresariais autorizados, escopo que a empresa executa, custos e responsável pela decisão.

O comprador envia arquivos por pasta privada autorizada. Nunca por issue pública, pull request, repositório ou comentário. Não solicitar senha de portal, certificado digital ou chave privada. Definir no pedido quem pode acessar os documentos e prazo de retenção/eliminação. Canal privado e identidade de cobrança precisam estar definidos antes da recepção real.

Prazo-base proposto: 2 dias úteis para Gate; 3 para Pack, a contar da confirmação de entrada completa, pagamento e disponibilidade de produção. Urgência de 24 horas somente depois de conferir volume e agenda. Não é cálculo de prazo processual nem promessa automática para todo edital.

Limite inicial para confirmação comercial: um edital, um CNPJ e um lote/objeto, até 150 páginas de fontes e 30 documentos da empresa, uma rodada consolidada de correções. Material excedente, múltiplos lotes ou complexidade especial recebem orçamento e prazo próprios antes do compromisso. Os limites delimitam esforço; todos os anexos aplicáveis continuam obrigatórios.

## Execução

1. Inventariar fontes e registrar data, versão, origem e páginas. Baixar retificações e comparar com o conjunto recebido.
2. Ler conjunto integral; marcar páginas ilegíveis como pendência, sem adivinhar texto.
3. Extrair requisitos por item e classificá-los separadamente da prova de atendimento.
4. Cruzar cada requisito com documento empresarial, página, validade e cobertura. Ausência não vira confirmação de incapacidade.
5. Registrar riscos de execução, custos não cobertos e premissas; pedir confirmação aos responsáveis técnico/financeiro quando necessário.
6. Conferir a matriz e os itens omitidos. Aprovação de revisão exige identificação e data do revisor.
7. Gerar o dossiê com gate.py. A saída apenas consolida a matriz fornecida; o código não lê edital nem substitui revisão.
8. Entregar por canal privado e registrar versão entregue e confirmação do destinatário.

## Semântica da decisão

PENDENTE: falta conjunto completo, documentos empresariais revisados ou revisão aprovada. NO-GO: revisão completa identifica requisito crítico confirmado não atendido. GO CONDICIONAL: revisão completa identifica pendências ou divergências, que precisam ser resolvidas antes do envio. GO: todos os itens da matriz atendidos após revisão declarada. Nenhum estado garante decisão do órgão, autenticidade da prova ou ausência de item omitido pelo revisor.

## Critérios de aceite

O comprador consegue localizar cada exigência; toda conclusão de atendimento aponta prova; pendências têm responsável e prazo; decisão é compatível com a matriz; arquivos abrem; hashes correspondem aos bytes entregues; limitações e versão das fontes estão descritas. O aceite refere-se à entrega contratada, não a vitória na disputa.

Alteração de edital, retificação ou documento após revisão exige nova conferência dos itens afetados e novo diretório de saída. Não reaproveitar flag de aprovação de revisão anterior.

## Uso técnico

Requisito: Python 3.10 ou posterior, biblioteca padrão. Uso demonstrado em Linux; Windows não homologado neste ciclo.

```bash
python licitagate/gate.py licitagate/examples/synthetic-case.json /tmp/licitagate-demo
python -m unittest discover -s licitagate -p 'test_*.py' -v
```

O diretório de saída deve ser novo. O programa grava decision.json, matrix.csv, report.html e provenance.json. HTML pode ser aberto localmente e impresso pelo navegador. CSV tem neutralização de fórmulas nos campos textuais. Nenhum arquivo é enviado à rede.

## Checklist comercial

Antes de aceitar pedido: escopo fechado, material disponível, responsável identificado, data confirmada, prestador/contratante identificados, condições de cobrança verificadas, canal privado funcionando. Depois: evidência de pagamento externo, entrega, aceite, horas efetivas e receita conciliada. Não usar o gate de conformidade como verificador de pagamento.
