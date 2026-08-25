# Plano Técnico: Importação Automática de Notas

## Histórico: tentativa via Rotina agendada (abandonada)

A primeira tentativa usou uma **Rotina agendada** (scheduled trigger)
deste ambiente Claude Code Remote, reaproveitando a conexão Gmail já
autorizada nesta sessão — evitando qualquer credencial nova. Na prática,
**não funciona**: a plataforma não propaga o conector do Gmail para
sessões disparadas por Rotina nesta conta/organização (confirmado em
produção — a sessão disparada tinha as ferramentas do GitHub mas nenhuma
ferramenta `mcp__Gmail__*`), e a própria API de criação de rotina recusou
o parâmetro `connectors` ("not available for this organization"). Ou
seja, é uma limitação de plataforma, não uma questão de configuração da
rotina. A rotina criada para isso foi apagada.

## Solução adotada: GitHub Actions + API do Gmail (OAuth)

Em vez de depender de uma sessão Claude, o próprio workflow
`.github/workflows/monitor.yml` passa a chamar a API do Gmail
diretamente, do mesmo jeito que já chama a brapi.dev e o Banco Central —
usando `requests` puro, sem biblioteca cliente do Google (menos
dependência, mesmo padrão do resto do projeto).

Isso exige uma credencial OAuth do Gmail (client id/secret + refresh
token) guardada como secret do GitHub — a única diferença real em relação
ao resto do sistema, que nunca teve nada além de tokens de API simples.
Mitigação: escopo mínimo (`gmail.readonly`), e o app OAuth authorizes só
a leitura, nunca escrita/envio de e-mail.

### Por que não quebra o que já funciona

- `scripts/import_notas_email.py` sai silenciosamente (`exit 0`) se os
  secrets do Gmail (`GMAIL_CLIENT_ID`, `GMAIL_CLIENT_SECRET`,
  `GMAIL_REFRESH_TOKEN`, `NOTA_PDF_SENHA`) não estiverem configurados —
  não é preciso nada além de mergear este código; o comportamento atual
  (monitor de bandas + dashboard) continua idêntico até o usuário
  terminar a configuração do OAuth.
- O step no workflow tem `continue-on-error: true` — mesmo se a API do
  Gmail falhar (token expirado, rede fora, etc.), o resto do workflow
  (monitor de bandas, dashboard) roda normalmente.
- Nunca sobrescreve nada: só *acrescenta* linhas em `transactions.csv` e
  `processed_notas.txt` (mesmo padrão "cresce pra frente" do resto do
  projeto).
- Se uma nota específica falhar ao processar (senha errada, produto não
  mapeado, PDF corrompido), só aquela nota é pulada — não vai para
  `processed_notas.txt`, então a próxima execução tenta de novo, e nenhum
  dado incerto é commitado.

### Passo a passo de cada execução (`scripts/import_notas_email.py`)

1. Se faltar algum dos 4 secrets do Gmail: imprime aviso e sai (exit 0).
2. Troca o refresh token por um access token (`POST
   oauth2.googleapis.com/token`).
3. `GET .../messages?q=from:noreply@rico.com.vc subject:"Nota de
   Negociação"` — lista de IDs de mensagem.
4. Compara com `config/processed_notas.txt` (arquivo local, já no
   checkout do Actions) — pula os já processados.
5. Para cada mensagem nova: `GET .../messages/{id}?format=raw` → decodifica
   base64url → usa o módulo `email` da stdlib do Python para extrair o
   anexo PDF (muito mais robusto que parsing manual de boundary MIME).
6. Decripta o PDF com `pikepdf` (senha = `NOTA_PDF_SENHA`) e extrai o
   texto de cada página com `pdfplumber`.
7. Regex extrai, por linha de operação: C/V, produto (mapeado via
   `TICKER_MAP`), quantidade, preço; e a data via "Data pregão" da mesma
   página.
8. Se um produto não está em `TICKER_MAP`: não adivinha — pula a nota
   inteira (`ProdutoNaoMapeado`), loga um aviso.
9. Acrescenta as linhas novas em `transactions.csv` e os IDs processados
   em `processed_notas.txt` (só depois de processar TODAS as mensagens
   novas com sucesso — um commit só).
10. O step seguinte do workflow commita os dois arquivos (mesmo padrão
    `git status --porcelain` + `git add` + `git commit` + `git push`
    usado para os outros arquivos "cresce pra frente" do projeto).
11. O monitor de bandas roda em seguida, no mesmo job — já vê a posição
    atualizada.

### Módulos

- `src/monitor/notas_rico.py` — lógica pura (sem rede): decodificar
  e-mail MIME, extrair anexo, parsear texto da nota, mapear tickers.
  100% testável com dados sintéticos.
- `scripts/import_notas_email.py` — orquestração (chamadas HTTP à API do
  Gmail, leitura/escrita dos arquivos do repo). Não testado
  automaticamente (precisa de rede/credencial real), só validado
  manualmente.

### Configuração necessária (usuário)

Ver `specs/003-importacao-automatica-notas/setup-gmail-oauth.md` para o passo a passo completo de criação
do projeto no Google Cloud, tela de consentimento OAuth, e obtenção do
refresh token. Resumo dos secrets a cadastrar no GitHub:

| Secret | Para quê |
|---|---|
| `GMAIL_CLIENT_ID` | ID do cliente OAuth criado no Google Cloud Console |
| `GMAIL_CLIENT_SECRET` | Segredo do mesmo cliente OAuth |
| `GMAIL_REFRESH_TOKEN` | Token de atualização obtido no fluxo de consentimento (não expira, a menos que revogado ou que o app fique preso em modo "Testing" — ver documento de setup) |
| `NOTA_PDF_SENHA` | 3 últimos dígitos do CPF/CNPJ do usuário (senha do PDF da Rico) |

## Mapeamento de tickers (nome do produto na nota → ticker de pregão)

| Nome na nota | Ticker |
|---|---|
| INVESTOVWRA | VWRA11 |
| IT NOW IDIV | DIVO11 |
| TREND OURO | GOLD11 |
| IT NOW B5P2 | B5P211 |
| IT NOW DIPCA | CDIB11 |

Se aparecer um produto novo (fora dessa tabela), o script não adivinha —
sinaliza a operação não reconhecida em vez de mapear errado.

## Formulário do dashboard: desativado, não removido

`src/monitor/dashboard.py`:
- `SHOW_TRANSACTION_FORM = False` (constante no topo do módulo).
- HTML do formulário isolado em `_FORM_SECTION_HTML`; JS isolado em
  `_FORM_SCRIPT_TEMPLATE`. `build_dashboard_html` só inclui os dois
  quando `SHOW_TRANSACTION_FORM` é `True` (via placeholders
  `{form_section}`/`{form_script}` no template principal).
- Reativar no futuro (se a automação por e-mail falhar) é só virar o
  flag para `True` — nenhum código precisa ser reescrito.

## Testes

- `dashboard.py`: teste cobrindo que o formulário NÃO aparece por padrão,
  e outro confirmando que `SHOW_TRANSACTION_FORM = True` ainda funciona
  (feature mantida, só desativada).
- `notas_rico.py`: testes com dados sintéticos (e-mail MIME fabricado,
  texto de nota fabricado, PDF criptografado com `pikepdf` na hora) —
  decodificação de e-mail, extração de anexo, parsing de operação/data,
  decriptação de PDF, e o caso de produto não mapeado (levanta
  `ProdutoNaoMapeado` em vez de adivinhar).
- `scripts/import_notas_email.py` não tem teste automatizado (depende de
  rede/credencial OAuth real) — validado manualmente em produção quando
  os secrets estiverem configurados (T14 em `tasks.md`). A lógica de
  parsing em si (a parte que importa acertar) já está coberta pelos
  testes de `notas_rico.py`.
