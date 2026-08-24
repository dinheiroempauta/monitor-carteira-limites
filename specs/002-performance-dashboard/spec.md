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
   (holdings atuais × preço de mercado do dia), **acumulada dia a dia a
   partir de quando o dashboard começa a rodar** — sem reconstruir o
   passado (decisão explícita do usuário: não precisa de histórico de
   preço). Cada execução diária acrescenta um ponto em
   `config/wealth_history.csv`.
4. **Performance nominal e real**: duas séries, também acumuladas dia a
   dia a partir de agora —
   - Nominal: valor total da carteira ÷ total aportado até hoje, menos 1.
   - Real: a mesma conta, descontando o IPCA acumulado desde o início do
     acompanhamento (fonte: API do Banco Central, série 433, gratuita e
     sem autenticação) — mostra o ganho real de poder de compra, não só o
     número bruto.
5. **Publicação**: uma página HTML estática, publicada de graça no GitHub
   Pages, atualizada automaticamente todo dia (mesmo workflow do monitor de
   bandas). Sem servidor, sem banco de dados.
6. **Registro de transação pelo próprio site**: um formulário na página
   (data, ticker, ação, quantidade, preço) grava a linha direto em
   `config/transactions.csv` via API do GitHub, chamada pelo navegador do
   usuário. Exige um token do GitHub (fine-grained, restrito a este
   repositório) que o usuário cola uma vez na página — fica salvo só no
   `localStorage` do navegador dele, nunca é enviado a nenhum lugar além de
   `api.github.com`. Opcionalmente, se o token também tiver permissão
   "Actions: Read and write", o formulário dispara o workflow na hora
   (`workflow_dispatch`) para recalcular sem esperar o próximo agendamento.

## Fora de escopo (v1)

- Reconstrução do passado: os gráficos de patrimônio e performance só
  existem a partir da data em que o dashboard começou a rodar — não há
  como saber o valor da carteira em datas anteriores sem histórico de
  preço (decisão do usuário: aceitar essa limitação em troca de
  simplicidade — sem depender de endpoint de histórico de preços).
- Taxas/corretagem/IR no cálculo de custo (só quantidade × preço executado).
- Suporte a proventos/dividendos recebidos (fica pra uma iteração futura).
- Vendas parciais com apuração de lucro (o registro aceita venda, mas o
  cálculo de custo médio pós-venda é simplificado — ver `plan.md`).
- Autenticação/autorização no formulário além do token do GitHub que o
  próprio usuário controla — a página não tem login nem backend próprio.

## Requisito não funcional

- Grátis: GitHub Pages, API do Banco Central e a brapi.dev (já em uso) não
  têm custo.

## Risco aceito: token do GitHub no navegador

O formulário de registro (requisito 6) exige que o usuário cole um token
de escrita do GitHub na própria página, guardado em `localStorage`. Isso é
diferente do resto do sistema, que nunca teve credencial nenhuma no lado
do cliente. Mitigação: o token deve ser *fine-grained* e restrito só a
este repositório (nunca um token clássico com acesso à conta toda) — o
pior cenário de vazamento é alguém escrever no próprio
`monitor-carteira-limites`, não ter acesso à conta do usuário. Decisão do
usuário, ciente do trade-off, em troca de poder registrar compras direto
pelo site em vez de editar o CSV manualmente no GitHub.
