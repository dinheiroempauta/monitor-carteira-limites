# Plano Técnico: Monitor de Limites de Carteira

## Stack

- **Python 3.11+**, sem framework web (não há UI nesta v1).
- `requests` para chamar a API HG Brasil e a API do Telegram.
- `PyYAML` para configuração (`config/portfolio.yaml`, `config/quotas.yaml`).
- `playwright` (Python) para o scraper opcional da B3.
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
  quotas.yaml         # posição atual (qty por ticker) — fonte de verdade,
                       # atualizada pelo scraper ou manualmente
src/monitor/
  __init__.py
  config.py           # carrega/valida os YAML
  prices.py           # cliente HG Brasil
  allocation.py       # cálculo de % atual, status de banda, plano de venda,
                       # sugestão de aporte
  telegram.py         # envio de mensagem via bot
  report.py           # monta o texto do relatório em pt-BR
  main.py             # orquestra tudo (entrypoint)
scripts/
  update_quotas_from_b3.py   # scraper best-effort (Playwright), escreve em
                              # config/quotas.yaml; nunca lança exceção para
                              # fora — só loga e sai com status de sucesso/falha
tests/
  test_allocation.py
.github/workflows/
  monitor.yml          # cron diário
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
source: manual   # manual | b3_scraper
holdings:
  B5P211: 0
  VWRA11: 0
  DIVO11: 0
  CDIB11: 0
  GOLD11: 0
```

## Fluxo do `main.py`

1. Carrega `portfolio.yaml` e `quotas.yaml`.
2. Busca preços na HG Brasil para os tickers de `portfolio.yaml`.
3. Calcula, por ativo: valor, % atual, status (`ok` / `abaixo_da_banda` /
   `acima_da_banda`).
4. Se houver algum fora da banda → gera plano de venda/compra (quantidade
   de cotas, arredondada para baixo, e valor aproximado) para cada ativo
   fora da banda, visando trazer de volta ao alvo.
5. Senão → gera sugestão de destino do próximo aporte (pesos proporcionais
   ao quanto cada ativo está abaixo do alvo).
6. Monta o relatório e envia por Telegram (ou imprime, se não configurado).

## Scraper B3 (`scripts/update_quotas_from_b3.py`)

- Login em `investidorcer.b3.com.br` com CPF/senha (`B3_CPF`, `B3_PASSWORD`
  como secrets).
- Navega até a posição consolidada / extrato de custódia e extrai
  quantidade por ticker.
- Escreve em `config/quotas.yaml` com `source: b3_scraper` e
  `updated_at: <hoje>`.
- **Qualquer falha (seletor não encontrado, captcha, timeout, layout
  mudou) é capturada**: o script loga o erro, não altera `quotas.yaml`, e
  termina com exit code distinto de erro — o workflow continua e usa a
  última posição salva.
- Roda **desligado por padrão** no workflow (`ENABLE_B3_SCRAPER=false`).
  O usuário liga explicitamente depois de validar rodando localmente:
  `python scripts/update_quotas_from_b3.py`.

## GitHub Actions (`monitor.yml`)

- Cron diário (ex.: 09:00 BRT).
- Steps: checkout → setup Python → instalar deps → (se
  `ENABLE_B3_SCRAPER=true`) instalar browsers do Playwright e rodar o
  scraper com `continue-on-error: true` → se `quotas.yaml` mudou, commit +
  push automático → rodar `main.py` com os secrets como env vars.
- Secrets necessários no repo: `HGBRASIL_KEY`, `TELEGRAM_BOT_TOKEN`,
  `TELEGRAM_CHAT_ID` e, opcionalmente, `B3_CPF`/`B3_PASSWORD`.

## Testes

`tests/test_allocation.py` cobre com números concretos:
- ativo acima do teto → aparece no plano de venda com valor correto;
- ativo abaixo do piso → aparece no plano de compra;
- todos dentro da banda → nenhuma venda, só sugestão de aporte;
- pesos da sugestão de aporte somam 100% e priorizam o mais desviado.
