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
- [x] T5 — `src/monitor/historical_prices.py`: cliente do histórico de
      preços da brapi.dev
- [x] T6 — `src/monitor/performance.py`: séries de patrimônio e
      performance nominal/real
- [x] T7 — `src/monitor/dashboard.py`: gera o HTML (Chart.js via CDN)
- [x] T8 — `scripts/build_dashboard.py`: entrypoint, escreve
      `docs/index.html`
- [x] T9 — `.github/workflows/monitor.yml`: cron adicional 1x/dia para
      gerar e publicar o dashboard
- [x] T10 — Testes cobrindo os módulos novos (dados sintéticos, sem bater
      na rede)
- [ ] T11 — Usuário: mandar as transações reais (data, ticker, quantidade,
      preço médio executado) para substituir o placeholder em
      `config/transactions.csv`
- [ ] T12 — Usuário: ativar GitHub Pages uma vez (*Settings > Pages >
      Source: branch `main`, pasta `/docs`*)
