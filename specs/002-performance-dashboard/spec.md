# Spec: Dashboard de Performance da Carteira

## Problema

O monitor de bandas (feature 001) responde "preciso agir agora?". Esta feature
responde uma pergunta diferente: "como minha carteira está indo?" — o usuário
quer acompanhar a evolução patrimonial e a performance (nominal e real, contra
inflação) ao longo do tempo, além de ver a composição atual, numa página só,
sem precisar abrir planilha nem app de terceiros.

## Requisitos funcionais

1. **Registro de transações**: o usuário informa cada compra (histórica, das
   notas de negociação, e futuras) como `data, ticker, quantidade, preço médio
   executado`. Isso substitui a edição manual de `config/quotas.yaml` — a
   posição atual de cada ativo passa a ser a soma das quantidades por ticker
   em `config/transactions.csv`.
2. **Composição %**: gráfico de pizza/donut com a alocação atual (mesmos dados
   já calculados pelo monitor de bandas).
3. **Patrimônio ao longo do tempo**: série temporal do valor total da carteira
   (quantidade possuída em cada data × preço de mercado naquela data), desde a
   primeira transação até hoje.
4. **Performance nominal e real**: duas séries —
   - Nominal: valor total da carteira ÷ total aportado até a data, menos 1.
   - Real: a mesma conta, descontando o IPCA acumulado do período (fonte:
     API do Banco Central, série 433, gratuita e sem autenticação) — mostra o
     ganho real de poder de compra, não só o número bruto.
5. **Publicação**: uma página HTML estática, publicada de graça no GitHub
   Pages, atualizada automaticamente todo dia (mesmo workflow do monitor de
   bandas). Sem servidor, sem banco de dados.

## Fora de escopo (v1)

- Taxas/corretagem/IR no cálculo de custo (só quantidade × preço executado).
- Suporte a proventos/dividendos recebidos (fica pra uma iteração futura).
- Vendas parciais com apuração de lucro (o registro aceita venda, mas o
  cálculo de custo médio pós-venda é simplificado — ver `plan.md`).
- Edição da página pelo próprio usuário (é só leitura/visualização).

## Requisito não funcional

- Grátis: GitHub Pages, API do Banco Central e a brapi.dev (já em uso) não
  têm custo.
