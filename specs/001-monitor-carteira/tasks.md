# Tasks

- [x] T1 — Config: `config/portfolio.yaml` com alvo/bandas reais do usuário
- [x] T2 — Config: `config/quotas.yaml` preenchido com a posição real do usuário
- [x] T3 — `src/monitor/config.py`: carregar e validar os YAML
- [x] T4 — `src/monitor/prices.py`: cliente brapi.dev (`quote`)
- [x] T5 — `src/monitor/allocation.py`: cálculo de status por banda, plano de
      venda/compra, sugestão de aporte
- [x] T6 — `tests/test_allocation.py`: cobrir os 4 cenários do plano
- [x] T7 — `src/monitor/telegram.py`: envio de mensagem via bot
- [x] T8 — `src/monitor/report.py`: montar texto do relatório em pt-BR
- [x] T9 — `src/monitor/main.py`: orquestração fim a fim
- [x] T10 — `.github/workflows/monitor.yml`: cron diário, secrets cadastrados,
      testado em produção com sucesso (relatório recebido no Telegram)
- [x] T11 — `README.md`: instruções de setup e de como editar quotas manualmente
- [x] T12 — Tentativa de scraper automático da posição B3: abandonada (login
      tem captcha, inviável sem humano presente) — decisão em `plan.md`
- [x] T13 — `config/last_status.yaml` + `load_last_status`/`save_last_status`
      em `config.py`: guarda status de banda do último alerta enviado
- [x] T14 — `main.py`: só envia Telegram quando o status muda desde o
      último alerta; relatório completo sempre vai pro log
- [x] T15 — `tests/test_config.py`: round-trip de load/save do last_status
- [x] T16 — `.github/workflows/monitor.yml`: cron a cada 30min no horário de
      pregão + commit automático do `last_status.yaml` quando um alerta sai
