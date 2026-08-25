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

Se o step de importação de e-mail (`Importar notas de negociação...`)
tiver alterado `config/transactions.csv` nessa execução, rode
`git pull` antes do passo 2 para não calcular em cima de uma posição
desatualizada.

## Passo 2 — calcular a alocação com o script

Rode, do root do repo, com os preços extraídos e o valor do aporte que o
usuário informou:

```bash
python3 scripts/aporte_rebalanceamento.py --aporte <VALOR> \
  --preco B5P211=<preço> --preco VWRA11=<preço> --preco DIVO11=<preço> \
  --preco CDIB11=<preço> --preco GOLD11=<preço>
```

(A lista de `--preco` deve cobrir todos os tickers de
`config/portfolio.yaml` — se o portfólio mudar, ajuste a lista.)

O script já imprime as duas tabelas em markdown prontas para colar na
resposta (situação atual / depois do aporte). Cole a saída como está —
não recalcule os números manualmente por cima.

## Lógica do algoritmo (para explicar ao usuário se perguntado)

`aporte_quotas_plan` (`src/monitor/allocation.py`) resolve em duas fases:

1. **Tira todo mundo da banda primeiro.** Qualquer ativo abaixo do piso
   da própria banda recebe cotas suficientes pra alcançá-lo (do mais
   distante do piso pro menos distante), mesmo que isso signifique não
   comprar nada de quem já está dentro da banda mas ainda abaixo do
   alvo. Sair da banda é sempre pior do que estar longe do alvo mas
   dentro dela.
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
(`test_aporte_quotas_plan_prioriza_tirar_todos_da_banda_antes_do_alvo`),
o caso de aporte pequeno demais, e o caso de nunca gastar mais que o
aporte. Rode `python3 -m pytest tests/test_allocation.py -q` depois de
qualquer mudança em `aporte_quotas_plan`.
