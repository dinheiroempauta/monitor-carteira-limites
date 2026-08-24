# monitor-carteira-limites

Monitor pessoal de alocação de carteira: avisa via Telegram quando algum
ativo saiu da banda de tolerância e é preciso vender/comprar para
rebalancear — ou, se ainda estiver dentro da banda, sugere como direcionar
o próximo aporte. Roda de graça, a cada 30min no horário de pregão, via
GitHub Actions — mas só manda mensagem quando o status de algum ativo
muda, não a cada execução.

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
3. A cada 30min (10h-18h, dias úteis), o workflow busca a cotação de cada
   ativo na API brapi.dev, calcula o % atual de cada um e compara com a
   banda. Isso usa ~1.680 requisições/mês, bem dentro do limite gratuito
   de 15 mil da brapi.dev.
4. `config/last_status.yaml` guarda o status (dentro/fora da banda) de
   cada ativo na última vez que um alerta foi enviado. Só manda mensagem
   no Telegram quando esse status muda para algum ativo (com uma margem
   de segurança perto da borda da banda, pra não alertar toda hora se um
   ativo ficar oscilando bem em cima do limite) — execuções sem mudança
   ficam silenciosas (o relatório completo sempre fica no log da
   execução, se você quiser conferir).
5. Se algum ativo saiu da banda, o alerta sempre prioriza resolver **só
   com aporte** (comprando o que falta, sem vender nada) quando isso é
   matematicamente possível. Só sugere venda quando não tem outro jeito —
   e nesse caso mostra as duas opções lado a lado, com um lembrete de que
   venda pode gerar IR. Se está tudo dentro da banda, manda uma sugestão
   de para onde direcionar o próximo aporte.
6. `config/history.csv` guarda a alocação (só %, sem R$) toda vez que um
   alerta é enviado — um histórico simples da evolução da carteira ao
   longo do tempo.
7. Qualquer falha inesperada (API fora do ar, erro de configuração) também
   vira uma mensagem no Telegram, para não passar batida.

**No Telegram, as mensagens mostram só percentuais das posições — nunca o
valor em R$ de cada ativo nem o total da carteira** (de propósito, para
não virar um lugar de ficar acompanhando o tamanho). Valores em R$
aparecem só nas partes acionáveis (quanto aportar, quanto vender). O log
da execução (aba Actions do GitHub) tem a versão completa, com valores,
se você quiser conferir.

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
