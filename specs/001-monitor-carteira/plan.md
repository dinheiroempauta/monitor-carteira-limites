# Plano Técnico: Monitor de Limites de Carteira

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
src/monitor/
  __init__.py
  config.py           # carrega/valida os YAML e o last_status.yaml
  prices.py           # cliente brapi.dev
  allocation.py       # cálculo de % atual, status de banda, plano de venda,
                       # sugestão de aporte
  telegram.py         # envio de mensagem via bot
  report.py           # monta o texto do relatório em pt-BR
  main.py             # orquestra tudo (entrypoint) + lógica de "só alerta
                       # se mudou"
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

1. Carrega `portfolio.yaml` e `quotas.yaml`.
2. Busca preços na brapi.dev para os tickers de `portfolio.yaml`.
3. Calcula, por ativo: valor, % atual, status (`ok` / `abaixo_da_banda` /
   `acima_da_banda`).
4. Se houver algum fora da banda → gera plano de venda/compra (quantidade
   de cotas, arredondada para baixo, e valor aproximado) para cada ativo
   fora da banda, visando trazer de volta ao alvo.
5. Senão → gera sugestão de destino do próximo aporte (pesos proporcionais
   ao quanto cada ativo está abaixo do alvo).
6. Monta o relatório e **sempre imprime no log**.
7. Compara `{ticker: status}` atual com o salvo em `last_status.yaml`. Se
   for igual (nada mudou desde o último alerta), encerra sem enviar
   Telegram. Se mudou (ou é a primeira execução), envia o relatório por
   Telegram e sobrescreve `last_status.yaml` com o status atual.

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
  secrets como env vars → se `last_status.yaml` mudou (ou seja, um alerta
  foi enviado nessa execução), commit + push automático de volta ao repo.
- Secrets necessários no repo: `BRAPI_TOKEN`, `TELEGRAM_BOT_TOKEN`,
  `TELEGRAM_CHAT_ID`.
- Uso de API estimado: 16 execuções/dia × 5 tickers × ~21 dias úteis/mês ≈
  1.680 requisições/mês, ante o limite de 15 mil do plano free da brapi.dev.

## Testes

`tests/test_allocation.py` cobre com números concretos:
- ativo acima do teto → aparece no plano de venda com valor correto;
- ativo abaixo do piso → aparece no plano de compra;
- todos dentro da banda → nenhuma venda, só sugestão de aporte;
- pesos da sugestão de aporte somam 100% e priorizam o mais desviado.
