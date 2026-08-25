# Plano Técnico: Importação Automática de Notas

## Por que isso não é um step do GitHub Actions

Todo o resto do sistema roda em `.github/workflows/monitor.yml`, de graça,
sem depender de nenhum ambiente externo. A leitura de e-mail não pode
seguir esse padrão: exigiria guardar credenciais OAuth do Gmail do
usuário como secret do GitHub (client id/secret + refresh token), o que é
bem mais invasivo e complexo de manter do que o restante do projeto.

Este ambiente (Claude Code Remote) já tem uma conexão Gmail autorizada
pelo usuário. A solução usa essa conexão via uma **Rotina agendada**
(scheduled trigger deste ambiente) que roda periodicamente e reusa a
mesma sessão/contexto — sem precisar de nenhuma credencial nova.

## Mecanismo: Rotina agendada

- Cron: `0 13 * * 1-5` (13h UTC = 10h BRT, dias úteis) — todas as notas
  observadas até agora chegaram antes das 09h12 UTC, então 13h UTC dá
  margem.
- Vinculada a esta mesma sessão (não cria sessão nova a cada disparo),
  para manter o contexto do projeto.
- Prompt da rotina inclui: a busca do Gmail (`from:noreply@rico.com.vc
  subject:"Nota de Negociação"`), a senha do PDF, a tabela de mapeamento
  de tickers, e o passo a passo de extração/gravação (replicando o que
  foi validado manualmente nesta sessão).

## Passo a passo de cada execução

1. `search_threads` com a query acima.
2. Para cada thread encontrado, comparar o `message id` com as linhas de
   `config/processed_notas.txt` (lido via API do GitHub). Pular os já
   processados.
3. Para cada novo: `get_message(messageFormat=RAW)` → decodificar base64
   (`raw`, base64url) → localizar a seção `Content-Disposition: attachment`
   do PDF dentro do MIME → decodificar o base64 do anexo → salvar como
   arquivo temporário.
4. Abrir o PDF com `pikepdf` usando a senha (3 últimos dígitos do CPF) →
   ler o texto (via leitura de PDF) → extrair, por linha de negociação:
   ticker (mapeado), C/V (compra/venda), quantidade, preço, data do
   pregão (do cabeçalho "Data pregão").
5. Acrescentar uma linha em `config/transactions.csv` por operação
   (`date,ticker,action,qty,price`), e o `message id` em
   `config/processed_notas.txt`.
6. Commitar as duas mudanças direto na `main` (mesmo owner/repo/branch
   usados pelo formulário da feature 002: `dinheiroempauta/monitor-
   carteira-limites`, branch `main`).
7. Disparar `workflow_dispatch` do `monitor.yml` (recalcula banda e
   dashboard).
8. Se não havia nota nova: não faz nada (sem commit, sem aviso).
9. Se algo falhar (PDF não abre com a senha, ticker não mapeado, layout
   inesperado): não commita nada parcial — melhor faltar uma transação
   por um dia do que gravar dado errado — e sinaliza na resposta da
   sessão (visível na próxima vez que o usuário abrir a conversa).

## Mapeamento de tickers (nome do produto na nota → ticker de pregão)

| Nome na nota | Ticker |
|---|---|
| INVESTOVWRA | VWRA11 |
| IT NOW IDIV | DIVO11 |
| TREND OURO | GOLD11 |
| IT NOW B5P2 | B5P211 |
| IT NOW DIPCA | CDIB11 |

Se aparecer um produto novo (fora dessa tabela), a rotina não adivinha —
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
- A extração/parsing de e-mail/PDF em si não tem teste automatizado nesta
  v1 — é executada pela Rotina (fora do `pytest`), validada manualmente
  nesta sessão contra as 5 notas reais do usuário antes de virar rotina.
