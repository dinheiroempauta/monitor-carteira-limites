# Spec: Monitor de Limites de Carteira

> **Atualização (feature 002)**: `config/quotas.yaml`, mencionado abaixo,
> foi substituído por `config/transactions.csv` — a posição atual passou a
> ser calculada a partir do histórico de transações, não editada
> diretamente. Ver [`specs/002-performance-dashboard/`](../002-performance-dashboard/).
> O restante deste documento é mantido como registro histórico da decisão
> original.

## Problema

O usuário mantém uma carteira de ETFs/FIIs na B3 com uma alocação-alvo por
ativo e bandas de tolerância ao redor desse alvo. Aportes novos devem ser a
forma preferida de corrigir desvios, mas quando o desvio é grande demais para
ser corrigido só com aporte, é preciso vender um ativo e comprar outro. O
usuário quer ser avisado automaticamente quando isso acontece, sem precisar
calcular manualmente.

## Alocação-alvo e bandas (dados reais do usuário)

| Ticker  | Alvo | Banda mín | Banda máx |
|---------|------|-----------|-----------|
| B5P211  | 40%  | 20%       | 50%       |
| VWRA11  | 30%  | 30%       | 50%       |
| DIVO11  | 20%  | 20%       | 40%       |
| CDIB11  | 5%   | 5%        | 15%       |
| GOLD11  | 5%   | 5%        | 10%       |

## Requisitos funcionais

1. **Preços**: obter a cotação atual de cada ativo via API brapi.dev
   (`https://brapi.dev/api/quote`). Tentamos primeiro a HG Brasil, mas a
   chave gratuita do usuário não teve acesso liberado ao endpoint de
   cotação em nenhum ticker (confirmado em produção, inclusive com ações
   líquidas como PETR4) — a brapi.dev tem plano free com 15 mil
   requisições/mês, mais que suficiente para 1 execução diária.
2. **Quantidade de cotas**: registrada manualmente pelo usuário em
   `config/quotas.yaml`, editado direto pelo site do GitHub sempre que
   comprar/vender. Tentamos automatizar via scraping da Área do Investidor
   B3 (`investidorcer.b3.com.br`), mas o login de lá exige resolver um
   captcha — inviável de automatizar sem o usuário presente, então essa
   via foi abandonada (decisão registrada em `plan.md`).
3. **Cálculo de alocação**: para cada ativo, calcular `valor = qty × preço`,
   `% atual = valor / valor_total`, e comparar com alvo e banda.
4. **Decisão**:
   - Se todos os ativos estão dentro da banda → **não** sugerir venda.
     Sugerir como direcionar o **próximo aporte** para se aproximar do alvo
     (maiores desvios negativos primeiro).
   - Se algum ativo está fora da banda (abaixo do mínimo ou acima do
     máximo) → calcular o plano de compra/venda que traz cada ativo fora
     da banda de volta ao alvo (usando o valor total atual da carteira).
     - Se esse plano não inclui nenhuma venda (só compra — os ativos que
       sobrariam já estão dentro da própria banda) → apresentar como
       **aporte necessário**, sem falar em venda nem IR.
     - Se o plano inclui venda → antes de sugerir vender, calcular se dá
       para resolver **só com aporte novo** (o aporte dilui os ativos que
       não o recebem e reforça os que recebem, sem vender nada). Se der,
       apresentar as duas opções lado a lado: (1) aporte, com valor exato
       por ticker; (2) venda + compra, com um lembrete de que venda pode
       gerar IR. Se não der (aporte necessário seria grande demais —
       mais de 2x o valor atual da carteira), apresentar só a opção de
       venda.
5. **Notificação orientada a mudança, com histerese**: enviar o relatório
   via Telegram só quando o status de banda (dentro/abaixo/acima) de algum
   ativo mudar em relação à última vez que um alerta foi enviado — não a
   cada execução. Entrar numa banda (ok → fora) é sempre reconhecido na
   hora; já a recuperação (fora → ok) exige uma margem de 1 ponto
   percentual além da borda, para não gerar vários alertas seguidos com um
   ativo oscilando bem em cima do limite. O status comparado fica salvo em
   `config/last_status.yaml`. Se as credenciais do Telegram não estiverem
   configuradas, imprimir o relatório no log de qualquer forma.
6. **Execução agendada**: rodar automaticamente a cada 30min no horário de
   pregão (10h-18h BRT, dias úteis) via GitHub Actions (grátis), sem
   depender de infraestrutura paga.
7. **Custo**: o sistema inteiro deve funcionar com serviços gratuitos (API
   brapi.dev plano free — ~1.680 requisições/mês nessa cadência, dentro do
   limite de 15 mil —, GitHub Actions, bot do Telegram).
8. **Privacidade das mensagens**: o texto enviado ao Telegram mostra só
   percentuais nas posições (nunca R$ de posição nem valor total da
   carteira), para não incentivar acompanhar o tamanho da carteira. Valores
   em R$ aparecem só nas partes acionáveis (quanto aportar, quanto
   vender). O log completo da execução (com valores) fica disponível na
   aba Actions do GitHub para quem quiser conferir.
9. **Histórico**: registrar em `config/history.csv` a alocação (só
   percentuais) toda vez que um alerta é enviado — permite ver a evolução
   da carteira ao longo do tempo.
10. **Alerta de falha**: qualquer erro inesperado na execução (API fora do
    ar, configuração inválida) também deve gerar uma mensagem no Telegram,
    para que uma falha silenciosa não passe despercebida.

## Requisitos não funcionais / riscos aceitos

- Nenhuma credencial (token brapi.dev, token do Telegram) deve ir para o
  repositório em texto puro — tudo via GitHub Actions Secrets / variáveis
  de ambiente.
- O cálculo de "resolve só com aporte" (item 4) é uma simulação de diluição
  baseada nos pesos de `contribution_suggestion` — não é uma otimização
  exaustiva de todas as formas possíveis de distribuir um aporte, mas cobre
  bem o caso comum de poucos ativos fora da banda.
- O lembrete de IR (item 4) é só um lembrete textual — o sistema não tem
  dado de preço médio/custo de aquisição, então não calcula o imposto real.

## Fora de escopo (v1)

- Execução automática de ordens de compra/venda (o sistema só recomenda).
- Suporte a múltiplas carteiras/corretoras simultâneas.
- Interface web — o output é relatório em texto (Telegram/log).
