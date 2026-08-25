# Tasks

- [x] T1 — Ler manualmente as 5 notas de negociação pendentes do Gmail
      (extração via `get_message(RAW)` + decodificação MIME/base64 +
      `pikepdf` com a senha), mapear os nomes de produto para os tickers
      de pregão, e substituir o placeholder de `config/transactions.csv`
      pelas transações reais
- [x] T2 — `config/processed_notas.txt`: registrar os IDs das 5
      mensagens já processadas, para a importação automática não
      reprocessá-las
- [x] T3 — `src/monitor/dashboard.py`: desativar o formulário de
      transação (`SHOW_TRANSACTION_FORM = False`), isolando HTML/JS em
      constantes próprias para reativação futura sem reescrever código
- [x] T4 — `tests/test_dashboard.py`: cobrir formulário desativado por
      padrão e reativável via flag
- [x] T5 — `specs/003-importacao-automatica-notas/`: esta spec/plano
- [x] T6 — Tentativa via Rotina agendada (Claude Code Remote):
      **abandonada** — a plataforma não propaga o conector Gmail para
      sessões disparadas por Rotina nesta conta (confirmado em produção
      e pela API, que recusa o parâmetro `connectors` para esta
      organização). Rotina apagada.
- [x] T7 — `src/monitor/notas_rico.py`: lógica pura de extração
      (decodificar e-mail MIME, extrair anexo PDF, decriptar, parsear
      texto da nota, mapear tickers) — com testes usando dados
      sintéticos, sem rede
- [x] T8 — `scripts/import_notas_email.py`: orquestração (API do Gmail
      via OAuth, leitura/escrita de `transactions.csv` e
      `processed_notas.txt`) — sai silenciosamente se os secrets do
      Gmail não estiverem configurados
- [x] T9 — `.github/workflows/monitor.yml`: novo step (com
      `continue-on-error: true`, não afeta o resto do workflow) chamando
      o script acima antes do monitor de bandas
- [x] T10 — `requirements.txt`: adiciona `pikepdf` e `pdfplumber`
- [ ] T11 — `specs/003-importacao-automatica-notas/setup-gmail-oauth.md`: passo a passo para o usuário
      criar o projeto no Google Cloud, a tela de consentimento OAuth, e
      obter o refresh token
- [ ] T12 — Usuário: seguir o passo a passo e cadastrar os secrets
      `GMAIL_CLIENT_ID`, `GMAIL_CLIENT_SECRET`, `GMAIL_REFRESH_TOKEN`,
      `NOTA_PDF_SENHA` no GitHub
- [ ] T13 — Usuário: decidir entre publicar o app OAuth (evita reautorizar
      a cada 7 dias, exige verificação do Google) ou manter em modo
      Testing (setup mais rápido, precisa reautorizar toda semana)
- [ ] T14 — Confirmar em produção que o workflow importa uma nota real
      nova corretamente (sem duplicar, sem quebrar o monitor de bandas se
      a importação falhar)
