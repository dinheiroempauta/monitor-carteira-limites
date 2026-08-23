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

1. **Preços**: obter a cotação atual de cada ativo via API HG Brasil
   (`https://api.hgbrasil.com/finance/stock_price`).
2. **Quantidade de cotas**: obter a posição (quantidade de cada ticker) de
   forma automática via scraping da Área do Investidor B3
   (`investidorcer.b3.com.br`, login por CPF — funciona para qualquer
   corretora, inclusive Rico). Deve haver **fallback manual**: se o scraping
   falhar (mudança no site, captcha, bloqueio), o sistema usa a última
   posição conhecida registrada em `config/quotas.yaml`, que o usuário pode
   editar à mão a qualquer momento, e avisa que os dados podem estar
   desatualizados.
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
5. **Notificação**: enviar o relatório via Telegram (bot). Se as credenciais
   não estiverem configuradas, imprimir o relatório no log.
6. **Execução agendada**: rodar automaticamente 1x por dia via GitHub
   Actions (grátis), sem depender de infraestrutura paga.
7. **Custo**: o sistema inteiro deve funcionar com serviços gratuitos (API
   HG Brasil plano free, GitHub Actions, bot do Telegram).

## Requisitos não funcionais / riscos aceitos

- O scraping da B3 é best-effort: pode quebrar a qualquer mudança no site
  ou bloqueio anti-bot, especialmente rodando em IPs de datacenter (GitHub
  Actions). Isso é aceito pelo usuário; o sistema nunca deve travar por
  causa disso — sempre cai para a posição manual salva.
- Nenhuma credencial (chave HG Brasil, senha/CPF da B3, token do Telegram)
  deve ir para o repositório em texto puro — tudo via GitHub Actions
  Secrets / variáveis de ambiente.
- O scraper de B3 fica **desligado por padrão** no workflow agendado
  (`ENABLE_B3_SCRAPER` precisa ser explicitamente ligado) até o usuário
  validar que funciona de forma estável na conta dele.

## Fora de escopo (v1)

- Execução automática de ordens de compra/venda (o sistema só recomenda).
- Suporte a múltiplas carteiras/corretoras simultâneas.
- Interface web — o output é relatório em texto (Telegram/log).
