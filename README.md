# monitor-carteira-limites

Monitor pessoal de alocação de carteira: avisa via Telegram quando algum
ativo saiu da banda de tolerância e é preciso vender/comprar para
rebalancear — ou, se ainda estiver dentro da banda, sugere como direcionar
o próximo aporte. Roda de graça, 1x por dia, via GitHub Actions.

Documentação completa da spec/plano/tasks em
[`specs/001-monitor-carteira/`](specs/001-monitor-carteira/).

## Como funciona

1. `config/portfolio.yaml` guarda a alocação-alvo e as bandas de tolerância
   (já preenchido com os seus valores).
2. `config/quotas.yaml` guarda a quantidade de cotas de cada ativo — é a
   sua posição atual. Pode ser atualizado manualmente ou pelo scraper
   experimental da B3 (veja abaixo).
3. Todo dia, o workflow busca a cotação de cada ativo na API HG Brasil,
   calcula o % atual de cada um e compara com a banda.
4. Se algum ativo estourou a banda, manda um alerta de venda/compra pelo
   Telegram. Se está tudo dentro da banda, manda uma sugestão de aporte.

## Configuração (secrets do GitHub)

Em *Settings > Secrets and variables > Actions* do repositório, cadastre:

| Secret | Para quê |
|---|---|
| `HGBRASIL_KEY` | chave da sua conta na API HG Brasil |
| `TELEGRAM_BOT_TOKEN` | token do bot que vai te avisar (crie um com o [@BotFather](https://t.me/BotFather)) |
| `TELEGRAM_CHAT_ID` | id do chat/usuário que vai receber o alerta |
| `B3_CPF` / `B3_PASSWORD` | opcional, só se for usar o scraper de posição da B3 |

Para ligar o scraper automático no cron do GitHub Actions, crie também a
*variable* (não secret) `ENABLE_B3_SCRAPER` com valor `true` — **só depois
de validar que ele funciona rodando localmente** (veja abaixo). Fica
desligado por padrão porque login automatizado em sites de instituição
financeira a partir de IPs de datacenter costuma cair em captcha/bloqueio
anti-bot.

## Atualizar sua posição (quantidade de cotas)

**Manual (sempre funciona):** edite `config/quotas.yaml` direto:

```yaml
holdings:
  B5P211: 120
  VWRA11: 45
  DIVO11: 60
  CDIB11: 30
  GOLD11: 20
```

**Automático (experimental):** rode localmente

```bash
pip install -r requirements.txt
playwright install chromium
export B3_CPF=seu_cpf
export B3_PASSWORD=sua_senha
python scripts/update_quotas_from_b3.py
```

Isso faz login na Área do Investidor da B3 (funciona para qualquer
corretora, já que a custódia dos seus ativos é sempre na B3, inclusive os
da Rico) e atualiza `config/quotas.yaml` com a posição real. Se o site
mudou de layout ou pedir captcha, o script falha de forma segura e não
mexe no arquivo — é só voltar a editar manualmente até ajustar os
seletores em `scripts/update_quotas_from_b3.py`.

## Rodar localmente

```bash
pip install -r requirements.txt
export HGBRASIL_KEY=...
export TELEGRAM_BOT_TOKEN=...   # opcional — sem isso, só imprime no terminal
export TELEGRAM_CHAT_ID=...
PYTHONPATH=src python -m monitor.main
```

## Testes

```bash
pip install -r requirements.txt
python -m pytest tests/ -v
```
