# Spec: Importação automática de notas de negociação (e-mail)

## Problema

O usuário registrava cada compra/venda manualmente — seja editando
`config/transactions.csv` pelo site do GitHub, seja pelo formulário do
dashboard (feature 002). Ele pediu para eliminar esse passo manual: a
corretora (Rico) já manda um e-mail com a nota de negociação (PDF) toda
vez que uma operação é liquidada — o sistema deve ler esse e-mail sozinho
e lançar a transação.

## Requisitos funcionais

1. **Checagem periódica do Gmail**: o próprio workflow do GitHub Actions
   (mesmo cron que já roda o monitor de bandas) busca, via API do Gmail,
   e-mails de `noreply@rico.com.vc` com assunto "Nota de Negociação" que
   ainda não foram processados.
2. **Extração do PDF**: o PDF vem anexado e protegido por senha (3
   últimos dígitos do CPF/CNPJ do usuário). O script obtém o e-mail em
   formato bruto (MIME/base64), extrai o anexo, decodifica e abre o PDF
   com a senha para ler o texto das operações (ticker, quantidade, preço,
   compra/venda, data do pregão).
3. **Mapeamento de tickers**: a nota usa o nome do produto ("INVESTOVWRA",
   "IT NOW IDIV", "TREND OURO", "IT NOW B5P2", "IT NOW DIPCA"), não o
   ticker de pregão — o script traduz para VWRA11/DIVO11/GOLD11/B5P211/
   CDIB11.
4. **Deduplicação**: cada e-mail processado tem seu ID de mensagem
   registrado em `config/processed_notas.txt`. O script nunca reprocessa
   um e-mail já nessa lista, mesmo que rode várias vezes.
5. **Gravação**: novas transações são acrescentadas a
   `config/transactions.csv` (mesmo arquivo usado pelo monitor de bandas
   e pelo dashboard) e o `processed_notas.txt` é atualizado — ambos
   commitados direto na `main`.
6. **Recálculo imediato**: a importação roda como o primeiro step do
   mesmo job do `monitor.yml`, antes do monitor de bandas — não precisa
   disparar nada à parte, o resto do job já vê a posição atualizada na
   mesma execução.
7. **Sem novidade, sem ruído**: se não há nota nova, a importação não faz
   nada (nem commit, nem mensagem).

## Fora de escopo (v1)

- Suporte a outras corretoras além da Rico (o formato do PDF e o e-mail
  são específicos da Rico; se o usuário trocar de corretora, o parsing
  precisa ser adaptado).
- OCR ou parsing 100% robusto a mudanças de layout da Rico — o parsing é
  por regex sobre o texto extraído do PDF; uma mudança de layout pode
  quebrar o reconhecimento de uma linha de operação. Nesse caso, a nota
  é pulada (não commitada) e reportada no log da execução, nunca
  processada com dado adivinhado.

## Decisão: GitHub Actions + API do Gmail, não Rotina do Claude

A primeira tentativa usou uma Rotina agendada deste ambiente Claude Code
Remote (reaproveitando a conexão Gmail já autorizada nesta sessão, sem
credencial nova). **Não funcionou**: a plataforma não propaga o conector
do Gmail para sessões disparadas por Rotina nesta conta — confirmado em
produção (a sessão disparada só tinha ferramentas do GitHub, nenhuma do
Gmail) e pela própria API de criação de Rotina, que recusa o parâmetro
`connectors` para esta organização. Detalhes em `plan.md`.

A solução adotada chama a API do Gmail direto do `monitor.yml`, com uma
credencial OAuth (client id/secret + refresh token) guardada como secret
do GitHub — o mesmo padrão usado para brapi.dev e Banco Central, só que
com um passo de setup manual mais longo (ver `specs/003-importacao-automatica-notas/setup-gmail-oauth.md`).

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

## Riscos aceitos

- **Senha do PDF** (3 últimos dígitos do CPF): guardada como secret do
  GitHub (`NOTA_PDF_SENHA`), nunca em texto no repositório. É só 3
  dígitos, não o CPF completo — não dá acesso a nada além desses PDFs
  específicos.
- **Credencial OAuth do Gmail** (`GMAIL_CLIENT_ID`/`GMAIL_CLIENT_SECRET`/
  `GMAIL_REFRESH_TOKEN`, secrets do GitHub): dá acesso de **leitura** ao
  Gmail do usuário (escopo `gmail.readonly`), pelo tempo que o token
  ficar válido. É uma superfície de risco maior que qualquer outra
  credencial deste projeto até agora — mitigada por: escopo só-leitura
  (nunca envio/exclusão de e-mail), token revogável a qualquer momento em
  myaccount.google.com/permissions, e por viver só como secret do GitHub
  (nunca em texto no repositório ou em logs).

## Requisito não funcional

- Grátis: usa a conexão Gmail já existente da conta do usuário e a API
  do GitHub (mesmo padrão do formulário da feature 002) — nenhum serviço
  pago novo.
