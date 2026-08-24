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
                     # load_quotas), série de patrimônio investido acumulado
  ipca.py           # cliente da API do Banco Central (série 433) — índice
                     # acumulado entre duas datas
  historical_prices.py  # cliente do endpoint histórico da brapi.dev
  dashboard.py      # monta o HTML final (Chart.js via CDN) a partir das
                     # séries calculadas
scripts/
  build_dashboard.py  # entrypoint: gera docs/index.html
docs/
  index.html          # publicado pelo GitHub Pages (Settings > Pages > main /docs)
```

`load_quotas()` em `config.py` passa a delegar para `transactions.py` (soma
das transações), em vez de ler `quotas.yaml`. `config/quotas.yaml` é removido.

## Cálculo de patrimônio ao longo do tempo

1. Lista todas as datas com transação, mais a data de hoje.
2. Para cada ticker, calcula a quantidade possuída em cada data (soma
   cumulativa das transações até aquela data).
3. Busca o preço de fechamento de cada ticker em cada data via histórico da
   brapi.dev (uma chamada por ticker, range desde a primeira transação).
4. Patrimônio(data) = soma, por ticker, de quantidade(data) × preço(data).

## Cálculo de performance

- Total investido até a data = soma cumulativa de `qty*price` das transações
  até aquela data (compras somam, vendas subtraem).
- Nominal(data) = patrimônio(data) / total_investido(data) - 1.
- Real(data) = (1 + Nominal(data)) / índice_ipca_acumulado(primeira_transação,
  data) - 1, usando a série 433 do Banco Central (mensal, gratuita, sem
  token: `https://api.bcb.gov.br/dados/serie/bcdata.sgs.433/dados?formato=json`).

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

## Testes

- `transactions.py`: posição atual correta com compra+venda; total investido
  acumulado correto.
- `ipca.py`: parsing da resposta da API (com um payload de exemplo, sem
  bater na rede no teste).
- `dashboard.py`: gera HTML válido a partir de séries sintéticas (não testa
  renderização visual, só que os dados certos aparecem no HTML gerado).
