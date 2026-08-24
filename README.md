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
   sua posição atual. Você edita esse arquivo direto pelo GitHub sempre
   que comprar/vender (veja abaixo). Chegamos a tentar automatizar isso
   com um scraper da Área do Investidor da B3, mas o login de lá tem
   captcha — não dá para automatizar sem você presente, então optamos
   pela edição manual, que é simples e não depende de nada quebrar.
3. Todo dia, o workflow busca a cotação de cada ativo na API brapi.dev,
   calcula o % atual de cada um e compara com a banda.
4. Se algum ativo estourou a banda, manda um alerta de venda/compra pelo
   Telegram. Se está tudo dentro da banda, manda uma sugestão de aporte.

## Configuração (secrets do GitHub)

Em *Settings > Secrets and variables > Actions* do repositório, cadastre:

| Secret | Para quê |
|---|---|
| `BRAPI_TOKEN` | token gratuito da sua conta na [brapi.dev](https://brapi.dev/dashboard) (plano free: 15 mil requisições/mês, cobre FIIs e ETFs) |
| `TELEGRAM_BOT_TOKEN` | token do bot que vai te avisar (crie um com o [@BotFather](https://t.me/BotFather)) |
| `TELEGRAM_CHAT_ID` | id do chat/usuário que vai receber o alerta |

## Atualizar sua posição (quantidade de cotas)

Sempre que comprar ou vender, edite `config/quotas.yaml` direto pelo site
do GitHub (abra o arquivo no repositório, clique no lápis de editar, ajuste
os números, salve/commit):

```yaml
holdings:
  B5P211: 120
  VWRA11: 45
  DIVO11: 60
  CDIB11: 30
  GOLD11: 20
```

## Rodar localmente

```bash
pip install -r requirements.txt
export BRAPI_TOKEN=...
export TELEGRAM_BOT_TOKEN=...   # opcional — sem isso, só imprime no terminal
export TELEGRAM_CHAT_ID=...
PYTHONPATH=src python -m monitor.main
```

## Testes

```bash
pip install -r requirements.txt
python -m pytest tests/ -v
```
