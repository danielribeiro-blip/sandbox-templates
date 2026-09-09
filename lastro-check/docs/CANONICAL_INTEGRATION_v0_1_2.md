# Lastro Check — integração canônica v0.1.2

Registro: 09/09/2026, BRT. Candidato de integração; não é autorização de produção.

## Origem comprovada

O pacote `LASTRO_CHECK_COMMERCIAL_CLOSURE_v1.zip` contém a distribuição
`lastro-commercial-v0.1.1.zip`, cujo SHA-256 é exatamente
`d384bbbbf0b62bb0dd7d10f274cc5358939f5580a1d7c962dfa6ff59ad0b124d`.
Os 27 checksums do kit conferem. Os 21 arquivos da distribuição original foram
recuperados; a baseline original passou seus quatro testes em seu próprio diretório.
O original foi preservado. O módulo interno declarava 0.1.0, enquanto os metadados
indicavam 0.1.1; o novo candidato unifica ambos em 0.1.2.

A camada complementar deriva do overlay v2 e da revisão v3.1 do commit
`7ac343bab15db115578a379c317d1025785533d6`. Os imports foram adaptados ao namespace
real `lastro`. O diretório `lastro-check` é a aplicação integrada; os overlays
históricos permanecem como evidência, sem substituírem a aplicação.

## Alterações executadas

- Matcher real usa valor, referência, janela temporal e decisão explícita de ambiguidade.
- CSV real aplica neutralização aos identificadores textuais; dinheiro não é convertido em texto de fórmula.
- CLI gera proveniência das fontes e saídas; recusa sobrescrever diretórios de resultado.
- Inventário recusa symlinks e saída dentro da árvore de entrada.
- Guard Ed25519 verifica os mesmos bytes que identifica pelo hash e retorna claims ao adapter comercial.
- Builder usa staging isolado e arquivos permitidos; bloqueia nomes sensíveis, PEM privado e symlinks; inspeciona o wheel final.
- Recibos vinculam pedido, cliente, projeto, versão, distribuição e relatórios.

## Evidência executada localmente

- Baseline canônica: 4 testes passaram.
- Candidato: 63 testes e 26 subtestes passaram.
- ZIP e wheel construídos; inspeção de distribuição passou.
- Wheel instalado em venv com dependências locais compartilhadas, executado fora do checkout.
- Demo: 4 vendas, 1 sem exceções, 3 com exceções; recibo validado.
- Testes negativos cobrem ambiguidade, referência fora da janela, adulteração de licença/relatório,
  identidade divergente, fórmula no identificador e segredo no staging.
- GitHub Actions configurado para Ubuntu e Windows. Resultado remoto deve ser verificado
  no commit; configuração de CI não equivale a execução aprovada.

## Utilidade comercial demonstrável

O componente permite ao integrador conferir vendas, repasses e banco a partir de
CSV local e entregar exceções rastreáveis. Pode reduzir o trabalho de conferência
manual em projetos delimitados; redução de horas ainda precisa ser medida em piloto.

Diferenciais implementados: implantação local, formatos portáteis, janela explícita,
ambiguidade conservadora, identificação do método de pareamento, hashes das fontes,
recibo verificável e vínculo comercial com cliente/projeto nomeados. A reutilização
do motor e dos testes em novos projetos é uma alavanca operacional; não comprova
exclusividade de mercado nem intenção de compra.

## Limites e próxima evidência necessária

Não há pagamento real comprovado neste registro. Demo, ordem e pagamento de teste
são sintéticos e não representam receita. O CLI não bloqueia automaticamente
execuções por licença: cabe à aplicação integradora chamar o runtime/guard.

Proveniência está no nível de arquivo e locator; não substitui validação material,
trilha assinada por terceiro ou auditoria independente. Duplicatas da adquirente
são sinalizadas; agrupamento de repasses, múltiplas moedas e conectores bancários
não foram implementados nesta integração. A conferência concorrente de arquivos
pressupõe fontes estáveis durante a execução.

Antes de produção: validar o resultado remoto Windows/Ubuntu, obter revisão externa
exigida para liberação e conectar verificação real de pagamento e credenciais de
operação. Nada disso impede testar o candidato com os exemplos sintéticos.


## Correção após execução remota

A primeira execução remota passou no Ubuntu e encontrou `WinError 32` no Windows:
o context manager de SQLite encerrava a transação sem fechar a conexão. O adapter
agora fecha explicitamente cada conexão e inicia transação IMMEDIATE antes de
consultar/reservar a referência de pagamento. Um teste concorrente assegura que
apenas um pedido pode reservar a mesma referência. Também foram incluídos PEM
privados ENCRYPTED, DSA e ED25519 na inspeção de distribuição. Nova execução
remota deve confirmar o commit final.
