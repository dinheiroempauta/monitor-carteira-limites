# Spec: Importação automática de notas de negociação (e-mail)

## Problema

O usuário registrava cada compra/venda manualmente — seja editando
`config/transactions.csv` pelo site do GitHub, seja pelo formulário do
dashboard (feature 002). Ele pediu para eliminar esse passo manual: a
corretora (Rico) já manda um e-mail com a nota de negociação (PDF) toda
vez que uma operação é liquidada — o sistema deve ler esse e-mail sozinho
e lançar a transação.

## Requisitos funcionais

1. **Checagem periódica do Gmail**: uma rotina agendada busca, no Gmail
   do usuário, e-mails de `noreply@rico.com.vc` com assunto "Nota de
   Negociação" que ainda não foram processados.
2. **Extração do PDF**: o PDF vem anexado e protegido por senha (3
   últimos dígitos do CPF/CNPJ do usuário). A rotina obtém o e-mail em
   formato bruto (MIME/base64), extrai o anexo, decodifica e abre o PDF
   com a senha para ler o texto das operações (ticker, quantidade, preço,
   compra/venda, data do pregão).
3. **Mapeamento de tickers**: a nota usa o nome do produto ("INVESTOVWRA",
   "IT NOW IDIV", "TREND OURO", "IT NOW B5P2", "IT NOW DIPCA"), não o
   ticker de pregão — a rotina traduz para VWRA11/DIVO11/GOLD11/B5P211/
   CDIB11.
4. **Deduplicação**: cada e-mail processado tem seu ID de mensagem
   registrado em `config/processed_notas.txt`. A rotina nunca reprocessa
   um e-mail já nessa lista, mesmo que rode várias vezes.
5. **Gravação**: novas transações são acrescentadas a
   `config/transactions.csv` (mesmo arquivo usado pelo monitor de bandas
   e pelo dashboard) e o `processed_notas.txt` é atualizado — ambos
   commitados direto na `main`.
6. **Disparo do recálculo**: depois de gravar, a rotina aciona
   `workflow_dispatch` do `monitor.yml` para recalcular banda e dashboard
   sem esperar o próximo agendamento.
7. **Sem novidade, sem ruído**: se não há nota nova, a rotina não faz
   nada (nem commit, nem mensagem).

## Fora de escopo (v1)

- Suporte a outras corretoras além da Rico (o formato do PDF e o e-mail
  são específicos da Rico; se o usuário trocar de corretora, o parsing
  precisa ser adaptado).
- Rodar como parte do GitHub Actions: a leitura do Gmail depende da
  conexão Gmail deste ambiente Claude (OAuth do usuário), que não existe
  dentro do runner do GitHub Actions. A automação roda como uma Rotina
  agendada deste ambiente (Claude Code Remote), não como um step do
  workflow.
- OCR ou parsing 100% robusto a mudanças de layout da Rico — como o
  parsing do texto do PDF é feito por leitura/interpretação (não regex
  rígido), mudanças de layout tendem a ser absorvidas, mas não há
  garantia formal.

## Decisão: desativar o formulário manual do dashboard

Com a importação automática rodando, o formulário de registro de
transação embutido no dashboard (feature 002, requisito 6) deixou de ser
o caminho principal. Decisão do usuário: **não excluir o código**
(mantém `dashboard.py` com o HTML/JS do formulário intactos, atrás de um
flag `SHOW_TRANSACTION_FORM = False`), só remover da página renderizada.
Justificativa: serve de contingência manual caso a importação automática
falhe (Gmail fora do ar, corretora muda o layout do PDF, etc.) — nesse
caso, basta trocar o flag para `True` para reativar o formulário sem
reescrever nada.

## Risco aceito: senha do PDF (últimos 3 dígitos do CPF) na Rotina

A Rotina agendada precisa da senha para abrir os PDFs. Ela fica salva no
prompt da Rotina (mecanismo de agendamento deste ambiente Claude), não em
nenhum secret do GitHub nem em texto no repositório. Mitigação: é só 3
dígitos (não o CPF completo), e o dado já vive nos e-mails da própria
conta do usuário — não é uma credencial de acesso a nada além desses
PDFs.

## Requisito não funcional

- Grátis: usa a conexão Gmail já existente da conta do usuário e a API
  do GitHub (mesmo padrão do formulário da feature 002) — nenhum serviço
  pago novo.
