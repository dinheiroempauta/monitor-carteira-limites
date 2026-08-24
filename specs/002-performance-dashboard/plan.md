# Plano Técnico: Dashboard de Performance

## Contratos de dados

`config/transactions.csv`:
```csv
date,ticker,action,qty,price
2026-01-10,B5P211,compra,65,105.20
2026-03-15,VWRA11,compra,10,112.40
```
- `action`: `compra` ou `venda`.
- Posição atual de um ticker = soma de `qty` das compras menos soma de `qty`
  das vendas.
- Total investido (para performance nominal) = soma de `qty*price` das
  compras menos soma de `qty*price` das vendas (saída de caixa reduz o total
  aportado à vista, não é tratado como "lucro" nesta v1 — ver limitação
  abaixo).

## Módulos novos

```
src/monitor/
  transactions.py   # carrega transactions.csv, calcula posição atual (substitui
                     # load_quotas), total investido acumulado até uma data
  ipca.py           # cliente da API do Banco Central (série 433) — índice
                     # acumulado entre duas datas
  performance.py    # retorno nominal e real, num único ponto no tempo (hoje)
  dashboard.py      # monta o HTML final (Chart.js via CDN) a partir da série
                     # acumulada em wealth_history.csv
scripts/
  build_dashboard.py  # entrypoint: calcula o ponto de hoje, acrescenta em
                       # wealth_history.csv, gera docs/index.html
docs/
  index.html          # publicado pelo GitHub Pages (Settings > Pages > main /docs)
config/
  wealth_history.csv  # série acumulada dia a dia (ver abaixo)
```

`load_quotas()` em `config.py` passa a delegar para `transactions.py` (soma
das transações), em vez de ler `quotas.yaml`. `config/quotas.yaml` é removido.

## Decisão: sem histórico de preço (só daqui pra frente)

A primeira versão tentava reconstruir o patrimônio desde a primeira
transação usando o endpoint de histórico de preços da brapi.dev
(`/api/quote/{ticker}?range=5y&interval=1d`). Rodando contra a API de
verdade, esse endpoint devolveu `400 Bad Request` para todos os tickers —
o `range`/`interval` corretos para o plano do usuário não foram
confirmados. Em vez de investigar mais, o usuário decidiu simplificar:
**os gráficos de patrimônio e performance só existem a partir de agora**,
sem tentar reconstruir o passado. Isso elimina de vez a dependência do
endpoint de histórico — `historical_prices.py` foi removido.

`config/wealth_history.csv` acumula um ponto por dia (`date, wealth,
invested, nominal_return, real_return`), escrito por
`config.append_wealth_history` — mesmo padrão de "cresce pra frente" já
usado em `history.csv` (feature 001). Rodar o dashboard mais de uma vez no
mesmo dia substitui a linha daquele dia em vez de duplicar.

## Cálculo de patrimônio e performance (ponto de hoje)

1. `holdings = current_holdings(transactions)` (soma das transações).
2. `wealth = Σ holdings[ticker] × preço_atual[ticker]` (preço atual, já
   buscado pelo monitor de bandas via brapi.dev — nenhuma chamada extra).
3. `invested = total_invested_at(transactions, hoje)`.
4. `nominal = wealth / invested - 1`.
5. `real = (1 + nominal) / índice_ipca_acumulado(primeira_transação, hoje) - 1`,
   usando a série 433 do Banco Central (mensal, gratuita, sem token:
   `https://api.bcb.gov.br/dados/serie/bcdata.sgs.433/dados?formato=json`).
   `None` se a API do IPCA falhar (o dashboard segue sem a linha "real").
6. Acrescenta `(hoje, wealth, invested, nominal, real)` em
   `wealth_history.csv`; os gráficos leem o arquivo inteiro (todos os
   pontos já acumulados) para desenhar as séries.

## Limitação aceita (venda)

O cálculo de "total investido" nesta v1 trata venda como uma redução linear
do total aportado (não apura lucro/prejuízo da venda separadamente). Para uma
carteira que só compra (o caso atual do usuário), isso é equivalente ao
correto. Se houver venda parcial no futuro, o número de "nominal" pode ficar
levemente impreciso — sinalizado no código com um comentário, não um bug
silencioso.

## Publicação (GitHub Pages)

- `docs/index.html` é gerado e commitado pelo workflow diário (mesmo job do
  monitor de bandas, um step a mais).
- Único passo manual do usuário, uma vez: `Settings > Pages > Source: branch
  main, folder /docs`. Depois disso, a URL fica fixa e atualiza sozinha.
- HTML usa Chart.js via CDN (`<script src="https://cdn.jsdelivr.net/npm/chart.js">`)
  — GitHub Pages não tem as restrições de CSP dos Artifacts, então CDN
  funciona normalmente.

## Formulário de transação (grava direto do navegador)

`build_dashboard_html` embute um formulário (data/ticker/ação/qtd/preço) e
o JS necessário pra chamar a API REST do GitHub direto do navegador do
usuário — sem backend próprio:

1. **Token**: um `<input type="password">` guarda o token em
   `localStorage['gh_token']` na primeira vez; nas próximas visitas o
   formulário já aparece pronto pra usar. Um link "trocar/remover token"
   limpa o `localStorage`.
2. **Salvar transação**: `GET /repos/{owner}/{repo}/contents/config/transactions.csv`
   (pega o conteúdo atual em base64 + `sha`), decodifica, acrescenta a
   linha nova, recodifica, e `PUT` no mesmo endpoint com o `sha` (exigido
   pela API do GitHub pra confirmar que não houve conflito de escrita
   concorrente) e a nova branch.
3. **Recalcular na hora (opcional)**: depois de salvar, tenta
   `POST /repos/{owner}/{repo}/actions/workflows/monitor.yml/dispatches`.
   Só funciona se o token também tiver escopo "Actions: Read and write";
   se falhar (403), o formulário só avisa que vai refletir na próxima
   execução agendada — não é tratado como erro.
4. **Constantes** (`REPO_OWNER`, `REPO_NAME`, `FILE_PATH`, `BRANCH`) vêm de
   `dashboard.py` (módulo Python), não hardcoded duas vezes no HTML —
   single source of truth caso o repo mude de nome/dono algum dia.

Risco aceito e mitigação em `spec.md` (token fine-grained restrito a este
repositório, nunca um token de conta inteira).

## Testes

- `transactions.py`: posição atual correta com compra+venda; total investido
  acumulado correto.
- `ipca.py`: parsing da resposta da API (com um payload de exemplo, sem
  bater na rede no teste).
- `performance.py`: retorno nominal e real com números concretos.
- `config.py`: round-trip de `wealth_history.csv`, incluindo substituir a
  linha do mesmo dia em vez de duplicar.
- `dashboard.py`: gera HTML válido a partir de uma série sintética (não
  testa renderização visual, só que os dados certos aparecem no HTML
  gerado, incluindo o formulário e as constantes de repo/branch/arquivo).
