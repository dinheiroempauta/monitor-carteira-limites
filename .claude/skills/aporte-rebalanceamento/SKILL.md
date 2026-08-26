---
name: aporte-rebalanceamento
description: >
  Calcula quantas cotas comprar de cada ativo da carteira com um valor de
  aporte, priorizando sempre tirar (ou manter) todos os ativos dentro da
  banda de tolerância antes de perseguir o alvo. Use quando o usuário
  informar um valor de aporte e pedir para saber o que comprar, quanto
  comprar de cada ativo, ou como se aproximar do alvo/enquadrar na banda.
---

# Aporte e rebalanceamento

Existe também um caminho que não depende desta skill nem de nenhum
agente: o próprio `monitor.yml` tem um campo `aporte` no
`workflow_dispatch` (visível no site/app do GitHub em "Run workflow").
Preenchido, um step dedicado (`scripts/calcular_aporte.py`) busca a
cotação, roda `aporte_quotas_plan` e manda o resultado direto no
Telegram — sem terminal, sem script local, sem assinatura de agente
nenhuma. Essa skill continua valendo para quando o pedido chega aqui no
chat (ex.: "/aporte-rebalanceamento, tenho R$X"), mas vale saber que o
usuário tem essa alternativa e pode preferir usá-la no dia a dia.

Processo determinístico em duas etapas — nunca faça a conta de cabeça ou
por estimativa: os preços vêm de uma execução real do workflow, e a
distribuição das cotas vem de um script testado (`aporte_quotas_plan` em
`src/monitor/allocation.py`), não de aritmética livre no chat.

## Por que não dá pra usar a brapi.dev direto

Esta sessão roda num sandbox cujo proxy de rede bloqueia `brapi.dev` (é
política do ambiente, não do projeto — não peça pro usuário "desbloquear"
nada). O `GITHUB_ACTIONS` do repositório é quem tem o `BRAPI_TOKEN` de
verdade. Por isso o processo é: aciona o workflow, lê o preço que ele
buscou, e só então calcula localmente.

## Passo 1 — obter preços reais via GitHub Actions

1. Dispare o workflow:
   `mcp__github__actions_run_trigger` com `method: run_workflow`,
   `workflow_id: monitor.yml`, `ref: main`, `owner`/`repo` do projeto.
2. Espere ~15-20s e liste as execuções recentes
   (`mcp__github__actions_list`, `method: list_workflow_runs`,
   `resource_id: monitor.yml`) até achar a que você disparou com
   `status: completed`.
3. Pegue o `job_id` dela (`mcp__github__actions_list`,
   `method: list_workflow_jobs`) e leia o log
   (`mcp__github__get_job_logs`, `return_content: true`).
4. No log, o step "Rodar monitor e notificar" imprime uma linha por
   ativo assim:
   `B5P211: 65 cotas × R$ 110.62 = R$ 7,190.30 (39.5% — alvo 40%, banda 20%-50%) ✅`
   Extraia o preço (`R$ 110.62`) de cada ticker — é o preço real do
   pregão no momento da execução.
5. Anote também o **timestamp dessa linha de log** (o campo de horário
   que a API do GitHub retorna junto de cada linha, ex.
   `2026-08-25T16:19:59.0597586Z`) — o passo 2 exige esse valor.

**Se o workflow falhar** (conclusion `failure`, ou o log não tiver as
linhas de preço — ex. brapi.dev fora do ar, `BRAPI_TOKEN` expirado): pare
aqui, avise o usuário no chat e não continue. Nunca estime, reaproveite
um preço de execução anterior, ou invente um timestamp pra contornar a
checagem do passo 2 — isso anularia a garantia inteira de preço real que
essa skill existe pra dar.

Se o step de importação de e-mail (`Importar notas de negociação...`)
tiver alterado `config/transactions.csv` nessa execução, rode
`git pull` antes do passo 2 para não calcular em cima de uma posição
desatualizada.

## Passo 2 — calcular a alocação com o script

Rode, do root do repo, com os preços e o timestamp extraídos do log, e o
valor do aporte que o usuário informou:

```bash
python3 scripts/aporte_rebalanceamento.py --aporte <VALOR> \
  --run-timestamp <timestamp da linha de log, passo 1.5> \
  --preco B5P211=<preço> --preco VWRA11=<preço> --preco DIVO11=<preço> \
  --preco CDIB11=<preço> --preco GOLD11=<preço>
```

(A lista de `--preco` deve cobrir todos os tickers de
`config/portfolio.yaml` — se o portfólio mudar, ajuste a lista.)

**`--run-timestamp` é obrigatório e é a garantia técnica de frescor**: o
script recusa rodar (`SystemExit`, sem gerar tabela nenhuma) se esse
horário tiver mais de 30 minutos de idade (`--max-idade-minutos` ajusta
o limite) ou estiver no futuro. Isso existe porque nada no código força
o passo 1 a ser seguido de fato — sem essa checagem, seria possível
colar preços velhos de uma conversa anterior e o script rodaria do mesmo
jeito. Se a checagem recusar, o caminho é disparar o workflow de novo
(passo 1), não aumentar `--max-idade-minutos` pra forçar passagem.

O script já imprime as duas tabelas em markdown prontas para colar na
resposta (situação atual / depois do aporte), com a idade dos preços
declarada no topo. Cole a saída como está — não recalcule os números
manualmente por cima.

## Lógica do algoritmo (para explicar ao usuário se perguntado)

`aporte_quotas_plan` (`src/monitor/allocation.py`) resolve em duas fases:

1. **Tira todo mundo da banda primeiro.** Enquanto houver ativo abaixo
   do piso da própria banda, compra 1 cota por vez de quem estiver,
   naquele momento, mais distante do próprio piso — recalculado a cada
   cota, não uma fila fixa. Isso intercala as compras entre os ativos
   urgentes: se o aporte não for grande o bastante pra zerar todos os
   desvios, o algoritmo nivela o que sobrou entre eles em vez de zerar
   um ativo e deixar outro sem nenhuma cota. Nunca compra nada de quem
   já está dentro da banda mas abaixo do alvo enquanto houver alguém
   fora dela — sair da banda é sempre pior do que estar longe do alvo
   mas dentro dela. E nunca compra um ativo que estourou o teto pra
   cima (isso só se resolve vendendo, fora do escopo desta skill).
2. **Com o que sobra, aproxima do alvo.** Compra 1 cota por vez do ativo
   mais distante do próprio alvo entre os que ainda estão abaixo dele,
   sem nunca ultrapassar o teto da banda de ninguém. Nunca reforça quem
   já está no alvo ou acima (ex.: um ativo que já ultrapassou o alvo,
   como CDIB11 no exemplo desta conversa, recebe 0 cotas).

Nunca vende. Se o aporte for pequeno demais para zerar todos os
desvios, o script mostra isso — o(s) ativo(s) que sobrarem fora da banda
aparecem com o status real (🔵 abaixo / 🔴 acima) nas tabelas, sem
inflar a certeza do resultado.

## Testes

`tests/test_allocation.py` cobre o cenário real desta conversa
(`test_aporte_quotas_plan_prioriza_tirar_todos_da_banda_antes_do_alvo`) e
cenários de carteira muito discrepante por alta/queda forte com aporte
insuficiente para corrigir tudo — o caso mais importante de validar,
porque é onde um algoritmo ganancioso ingênuo erra:

- `test_queda_forte_de_um_ativo_aporte_pequeno_compra_o_maximo_possivel`:
  ativo despenca, aporte pequeno demais — gasta o máximo de cotas
  inteiras possível, nunca mais que o aportado, e o status final não
  esconde que ainda ficou fora da banda.
- `test_alta_forte_de_um_ativo_nunca_recebe_compra_mesmo_estourando_a_banda`:
  ativo dispara e estoura o teto — nunca recebe nenhuma cota (só venda
  resolve isso), o aporte inteiro vai para quem está diluído abaixo do
  piso.
- `test_crash_generalizado_aporte_insuficiente_nivela_em_vez_de_zerar_um_so`:
  vários ativos abaixo do piso ao mesmo tempo, aporte insuficiente pra
  todos — confirma que a compra intercala entre eles (nivela os desvios)
  em vez de zerar o maior e deixar os outros sem nenhuma cota.

`tests/test_aporte_rebalanceamento.py` cobre a checagem de frescor do
script: aceita timestamp recente, recusa timestamp velho (>30min por
padrão) e recusa timestamp no futuro (sinal de horário copiado errado).

Rode `python3 -m pytest -q` depois de qualquer mudança em
`aporte_quotas_plan` ou na checagem de frescor.
