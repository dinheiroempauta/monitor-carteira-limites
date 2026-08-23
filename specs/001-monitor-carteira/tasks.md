# Tasks

- [x] T1 — Config: `config/portfolio.yaml` com alvo/bandas reais do usuário
- [x] T2 — Config: `config/quotas.yaml` (placeholder, a preencher pelo usuário
      ou pelo scraper)
- [x] T3 — `src/monitor/config.py`: carregar e validar os YAML
- [x] T4 — `src/monitor/prices.py`: cliente HG Brasil (`stock_price`)
- [x] T5 — `src/monitor/allocation.py`: cálculo de status por banda, plano de
      venda/compra, sugestão de aporte
- [x] T6 — `tests/test_allocation.py`: cobrir os 4 cenários do plano
- [x] T7 — `src/monitor/telegram.py`: envio de mensagem via bot
- [x] T8 — `src/monitor/report.py`: montar texto do relatório em pt-BR
- [x] T9 — `src/monitor/main.py`: orquestração fim a fim
- [x] T10 — `scripts/update_quotas_from_b3.py`: scraper best-effort
- [x] T11 — `.github/workflows/monitor.yml`: cron diário
- [x] T12 — `README.md`: instruções de setup (secrets, como rodar local, como
      editar quotas manualmente)
- [ ] T13 — Usuário: preencher `config/quotas.yaml` com a posição real (ou
      validar o scraper localmente) e cadastrar os secrets no GitHub
