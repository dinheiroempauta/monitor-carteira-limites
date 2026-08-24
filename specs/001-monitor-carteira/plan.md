# Plano Técnico: Monitor de Limites de Carteira

> **Atualização (feature 002)**: `config/quotas.yaml` foi substituído por
> `config/transactions.csv` (ver [`specs/002-performance-dashboard/`](../002-performance-dashboard/)).
> `load_quotas()` em `config.py` hoje delega para `transactions.py`. O
> restante deste documento descreve o desenho original, mantido como
> registro histórico.

## Stack

- **Python 3.11+**, sem framework web (não há UI nesta v1).
- `requests` para chamar a API brapi.dev e a API do Telegram.
- `PyYAML` para configuração (`config/portfolio.yaml`, `config/quotas.yaml`).
- `pytest` para testar a lógica de alocação (é a parte que envolve dinheiro
  — precisa estar correta).
- **GitHub Actions** como agendador (cron), gratuito.
- **Telegram Bot API** para notificação, gratuito.

Tudo grátis: sem servidor, sem banco de dados (estado vive em arquivos YAML
versionados no próprio repo).

## Estrutura de diretórios

```
config/
  portfolio.yaml      # alvo e bandas por ticker (dado fixo do usuário)
  quotas.yaml         # posição atual (qty por ticker) — editado manualmente
                       # pelo usuário sempre que compra/vende
  last_status.yaml     # status de banda (por ticker) na última vez que um
                       # alerta foi enviado — usado para detectar mudança
  history.csv          # alocação (só %) a cada alerta enviado — histórico
src/monitor/
  __init__.py
  config.py           # carrega/valida os YAML, last_status.yaml e history.csv
  prices.py           # cliente brapi.dev
  allocation.py       # % atual, status de banda, plano de venda/compra,
                       # sugestão de aporte, resolução via aporte (dilução),
                       # status com histerese pra alerta
  telegram.py         # envio de mensagem via bot
  report.py           # monta o texto do relatório em pt-BR (versão log,
                       # com R$, e versão Telegram, só %)
  main.py             # orquestra tudo (entrypoint), lógica de "só alerta
                       # se mudou" e notificação de falha
tests/
  test_allocation.py
  test_config.py
.github/workflows/
  monitor.yml          # cron a cada 30min no horário de pregão
requirements.txt
.env.example
```

## Contratos de dados

`config/portfolio.yaml`:
```yaml
assets:
  B5P211: {target: 0.40, min: 0.20, max: 0.50}
  VWRA11: {target: 0.30, min: 0.30, max: 0.50}
  DIVO11: {target: 0.20, min: 0.20, max: 0.40}
  CDIB11: {target: 0.05, min: 0.05, max: 0.15}
  GOLD11: {target: 0.05, min: 0.05, max: 0.10}
```

`config/quotas.yaml`:
```yaml
updated_at: "2026-08-23"
source: manual
holdings:
  B5P211: 0
  VWRA11: 0
  DIVO11: 0
  CDIB11: 0
  GOLD11: 0
```

## Fluxo do `main.py`

1. Carrega `portfolio.yaml` e `quotas.yaml`. Qualquer erro daqui em diante
   (config inválida, falha na API de preços, exceção inesperada) é
   capturado e vira uma notificação de falha no Telegram (best-effort),
   além de log — nunca falha em silêncio.
2. Busca preços na brapi.dev para os tickers de `portfolio.yaml` (uma
   chamada por ticker — o plano free não permite consulta em lote).
3. Calcula, por ativo: valor, % atual, status (`ok` / `abaixo_da_banda` /
   `acima_da_banda`).
4. Gera o plano de venda/compra (`rebalance_plan`) para os ativos fora da
   banda, e a sugestão de aporte (`contribution_suggestion`) para o caso
   de estar tudo ok.
5. Se o plano tem alguma venda: calcula `resolve_via_aporte` (ver
   `allocation.py` abaixo) pra oferecer a alternativa de não vender nada.
   Se o plano só tem compra (sem venda), não precisa dessa etapa — já é,
   na prática, um aporte.
6. Monta duas versões do relatório (`report.py`): uma completa (com R$),
   sempre impressa no log; uma pro Telegram (só %, sem valor de posição).
7. Compara `{ticker: status}` atual, ajustado por histerese
   (`effective_status_for_alerting`), com o salvo em `last_status.yaml`.
   Se for igual (nada mudou desde o último alerta), encerra sem enviar
   Telegram. Se mudou (ou é a primeira execução), envia o relatório
   versão Telegram, sobrescreve `last_status.yaml` com o status
   (ajustado) atual, e acrescenta uma linha em `history.csv`.

## `resolve_via_aporte` (allocation.py)

Recebe os `statuses` atuais (já sabendo que há pelo menos uma venda no
plano). Usa os mesmos pesos de `contribution_suggestion` (proporcional ao
quanto cada ativo está abaixo do alvo) para simular: "se eu aportar X
reais, distribuídos assim, todo mundo fica dentro da banda?" — um aporte
dilui (reduz o %) dos ativos que não o recebem e reforça os que recebem.

Como um aporte grande demais pode diluir um ativo que já estava ok para
*fora* do próprio piso dele (ex.: um ativo com peso zero na distribuição,
que só recebe diluição, nunca reforço), a região de aportes que resolve
tudo não é necessariamente "qualquer valor grande" — pode ser um intervalo
fechado, ou não existir. A implementação varre o intervalo `[0, 2×valor
total da carteira]` em passos, localiza a transição de "não resolve" para
"resolve", refina com busca binária, e retorna `None` se nenhum ponto
varrido resolve (nesse caso, só a opção de venda é mostrada).

## `effective_status_for_alerting` (allocation.py)

Histerese de 1 ponto percentual só na direção de *recuperação* (fora da
banda → ok): entrar numa banda é sempre reconhecido na hora (sinal real,
sem atraso); só sair de "abaixo"/"acima" para "ok" exige que o % esteja
claramente dentro da banda (com a margem), não só tecnicamente dentro —
evita alertar de novo a cada oscilação pequena bem em cima do limite.

## Decisão: scraper de posição da B3 abandonado

Chegamos a implementar um scraper (Playwright) da Área do Investidor B3
(`investidorcer.b3.com.br`) para preencher `quotas.yaml` automaticamente.
Testando com credenciais reais do usuário, a tela de senha carrega um
captcha (`Carregando Captcha...`, confirmado via DevTools) — inviável de
resolver sem um humano presente, em qualquer ambiente (local ou CI). Como
o objetivo era automação sem intervenção manual, essa via foi abandonada
e o código removido. `config/quotas.yaml` é atualizado manualmente pelo
usuário (edição direta pelo site do GitHub), que é simples, confiável e
não depende de nada que possa quebrar.

## GitHub Actions (`monitor.yml`)

- Cron `*/30 13-21 * * 1-5` (a cada 30min, 10h-18h BRT, dias úteis; BRT é
  UTC-3 fixo, sem horário de verão no Brasil desde 2019).
- Steps: checkout → setup Python → instalar deps → rodar `main.py` com os
  secrets como env vars → se `last_status.yaml` ou `history.csv` mudou
  (ou seja, um alerta foi enviado nessa execução), commit + push
  automático de volta ao repo. Usa `git status --porcelain` (não `git
  diff`) porque `history.csv` pode ser um arquivo novo/não rastreado.
- Secrets necessários no repo: `BRAPI_TOKEN`, `TELEGRAM_BOT_TOKEN`,
  `TELEGRAM_CHAT_ID`.
- Uso de API estimado: 16 execuções/dia × 5 tickers × ~21 dias úteis/mês ≈
  1.680 requisições/mês, ante o limite de 15 mil do plano free da brapi.dev.

## Testes

`tests/test_allocation.py` cobre com números concretos:
- ativo acima do teto → aparece no plano de venda com valor correto;
- ativo abaixo do piso → aparece no plano de compra;
- todos dentro da banda → nenhuma venda, só sugestão de aporte;
- pesos da sugestão de aporte somam 100% e priorizam o mais desviado;
- `resolve_via_aporte` retorna `None` quando tudo já está ok;
- `resolve_via_aporte` calcula um valor que, simulado, traz tudo pra
  dentro da banda, quando existe solução só de aporte;
- `resolve_via_aporte` retorna `None` quando resolver via aporte
  quebraria outro ativo (cenário real: diluir o suficiente pra corrigir
  3 ativos abaixo do alvo derrubaria um 4º, hoje ok, pro fora da banda);
- `effective_status_for_alerting` segura a recuperação (fora → ok) até
  ter margem, mas reconhece entrada em breach (ok → fora) na hora.

`tests/test_config.py` cobre round-trip de `last_status.yaml` e o
acúmulo de linhas em `history.csv` (cabeçalho criado na primeira
chamada).
