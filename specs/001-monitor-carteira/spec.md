# Spec: Monitor de Limites de Carteira

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
     máximo) → sinalizar necessidade de **rebalanceamento por venda**,
     indicando quais ativos vender (os acima do teto) e quais comprar (os
     abaixo do piso), com valores e quantidade aproximada de cotas.
5. **Notificação orientada a mudança**: enviar o relatório via Telegram só
   quando o status de banda (dentro/abaixo/acima) de algum ativo mudar em
   relação à última vez que um alerta foi enviado — não a cada execução.
   O status comparado fica salvo em `config/last_status.yaml`. Se as
   credenciais do Telegram não estiverem configuradas, imprimir o
   relatório no log de qualquer forma.
6. **Execução agendada**: rodar automaticamente a cada 30min no horário de
   pregão (10h-18h BRT, dias úteis) via GitHub Actions (grátis), sem
   depender de infraestrutura paga.
7. **Custo**: o sistema inteiro deve funcionar com serviços gratuitos (API
   brapi.dev plano free — ~1.680 requisições/mês nessa cadência, dentro do
   limite de 15 mil —, GitHub Actions, bot do Telegram).

## Requisitos não funcionais / riscos aceitos

- Nenhuma credencial (token brapi.dev, token do Telegram) deve ir para o
  repositório em texto puro — tudo via GitHub Actions Secrets / variáveis
  de ambiente.

## Fora de escopo (v1)

- Execução automática de ordens de compra/venda (o sistema só recomenda).
- Suporte a múltiplas carteiras/corretoras simultâneas.
- Interface web — o output é relatório em texto (Telegram/log).
