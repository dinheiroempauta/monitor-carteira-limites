# Tasks

- [x] T1 — Ler manualmente as 5 notas de negociação pendentes do Gmail
      (extração via `get_message(RAW)` + decodificação MIME/base64 +
      `pikepdf` com a senha), mapear os nomes de produto para os tickers
      de pregão, e substituir o placeholder de `config/transactions.csv`
      pelas transações reais
- [x] T2 — `config/processed_notas.txt`: registrar os IDs das 5
      mensagens já processadas, para a rotina não reprocessá-las
- [x] T3 — `src/monitor/dashboard.py`: desativar o formulário de
      transação (`SHOW_TRANSACTION_FORM = False`), isolando HTML/JS em
      constantes próprias para reativação futura sem reescrever código
- [x] T4 — `tests/test_dashboard.py`: cobrir formulário desativado por
      padrão e reativável via flag
- [x] T5 — `specs/003-importacao-automatica-notas/`: esta spec/plano
- [ ] T6 — Criar a Rotina agendada (Claude Code Remote) que roda a
      checagem periódica do Gmail e replica o fluxo de extração/gravação
      validado manualmente no T1
- [ ] T7 — Acompanhar as primeiras execuções da rotina e confirmar que
      novas notas são importadas corretamente e sem duplicar
