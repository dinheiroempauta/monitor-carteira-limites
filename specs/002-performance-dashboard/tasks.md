# Tasks

- [x] T1 — `src/monitor/transactions.py`: registro de transações, posição
      atual, posição/total investido em qualquer data
- [x] T2 — `config.py`: `load_quotas`/`load_quotas_metadata` passam a
      delegar para `transactions.py`; `config/quotas.yaml` removido
- [x] T3 — `config/transactions.csv`: migrado com a posição atual como
      placeholder (mesma quantidade, preço de mercado do dia como custo
      aproximado) — **precisa ser substituído pelas transações reais**
      (data e preço de cada compra) assim que o usuário mandar
- [x] T4 — `src/monitor/ipca.py`: cliente da série 433 do Banco Central
- [x] T5 — Tentativa de reconstruir o patrimônio desde a 1ª transação via
      histórico de preço da brapi.dev: **abandonada** — endpoint retornou
      `400 Bad Request` em produção; usuário decidiu simplificar para "só
      daqui pra frente" (decisão em `plan.md`). `historical_prices.py`
      removido.
- [x] T6 — `src/monitor/performance.py`: retorno nominal e real num único
      ponto no tempo (hoje), sem depender de histórico de preço
- [x] T7 — `config.py`: `append_wealth_history`/`load_wealth_history` —
      série acumulada dia a dia em `config/wealth_history.csv`
- [x] T8 — `src/monitor/dashboard.py`: gera o HTML (Chart.js via CDN) a
      partir da série acumulada
- [x] T9 — `scripts/build_dashboard.py`: entrypoint, calcula o ponto de
      hoje e escreve `docs/index.html`
- [x] T10 — `.github/workflows/monitor.yml`: cron adicional 1x/dia para
      gerar e publicar o dashboard
- [x] T11 — Testes cobrindo os módulos novos (dados sintéticos, sem bater
      na rede)
- [ ] T12 — Usuário: mandar as transações reais (data, ticker, quantidade,
      preço médio executado) para substituir o placeholder em
      `config/transactions.csv`
- [ ] T13 — Usuário: ativar GitHub Pages uma vez (*Settings > Pages >
      Source: branch `main`, pasta `/docs`*)
- [ ] T14 — Confirmar em produção que a run diária do dashboard passa sem
      erro (primeira tentativa falhou no histórico de preço — corrigida
      pela T5; falta confirmar a versão nova)
