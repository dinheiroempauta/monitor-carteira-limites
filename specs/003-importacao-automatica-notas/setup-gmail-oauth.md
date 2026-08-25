# Passo a passo: liberar o Gmail para a importação automática

Isso é feito **uma vez só**. Ao final, você vai ter 4 valores para colar
como "secrets" no GitHub (a mesma tela de Settings > Secrets que você já
usou para o `BRAPI_TOKEN` e o Telegram).

Reserve uns 15-20 minutos. Siga os passos **na ordem**, sem pular.

---

## Parte 1 — Criar o projeto no Google Cloud

1. Acesse **console.cloud.google.com** e faça login com a mesma conta
   Google/Gmail que recebe as notas da Rico.
2. No topo da página, ao lado do logo "Google Cloud", clique no seletor
   de projeto (geralmente escrito "Select a project" ou o nome de algum
   projeto existente).
3. Clique em **"New Project"** (Novo projeto).
4. Em "Project name", escreva algo como `monitor-carteira` (o nome não
   importa, é só pra você identificar depois).
5. Clique em **"Create"**. Espere uns 10-20 segundos até a notificação de
   "criado" aparecer (sino no canto superior direito).
6. Confirme que o projeto novo está selecionado no seletor do topo (às
   vezes é preciso clicar em "Select project" de novo e escolher o que
   você acabou de criar).

## Parte 2 — Ativar a API do Gmail

1. Na barra de busca do topo (não é o seletor de projeto, é a busca
   geral), digite **"Gmail API"** e clique no resultado "Gmail API".
2. Clique no botão azul **"Enable"** (Ativar). Espere carregar.

## Parte 3 — Tela de consentimento OAuth

1. No menu lateral esquerdo (ícone ☰ se estiver escondido), vá em
   **"APIs & Services" > "OAuth consent screen"**.
2. Em "User Type", escolha **"External"** e clique em **"Create"**.
3. Preencha:
   - **App name**: `Monitor Carteira` (ou outro nome, não importa).
   - **User support email**: seu e-mail (selecione na lista).
   - Role até "Developer contact information" e coloque seu e-mail de
     novo.
4. Clique em **"Save and Continue"**.
5. Na tela **"Scopes"**, clique em **"Add or Remove Scopes"**.
   - Na caixa de busca/filtro, procure por `gmail.readonly`.
   - Marque o checkbox de **`.../auth/gmail.readonly`** (descrição: "Read
     all resources and their metadata—no write operations").
   - Clique em **"Update"** no rodapé do painel que abriu.
   - Clique em **"Save and Continue"**.
6. Na tela **"Test users"**, clique em **"Add Users"** e digite o
   **mesmo e-mail Gmail** que recebe as notas da Rico. Clique em
   **"Add"**, depois **"Save and Continue"**.
7. Na última tela ("Summary"), clique em **"Back to Dashboard"**.

> Isso deixa o app em modo **"Testing"**. Funciona normalmente, só que o
> token precisa ser renovado a cada 7 dias (você decide depois — T13 na
> `tasks.md` — se quer publicar o app pra evitar isso; não precisa
> decidir agora pra seguir os próximos passos).

## Parte 4 — Criar as credenciais (Client ID e Client Secret)

1. Menu lateral: **"APIs & Services" > "Credentials"**.
2. Clique em **"+ Create Credentials"** (topo) > **"OAuth client ID"**.
3. Em "Application type", escolha **"Web application"** (não escolha
   "Desktop app" — importante, precisa ser Web application).
4. Em "Name", pode deixar o padrão ou escrever `monitor-carteira-web`.
5. Em **"Authorized redirect URIs"**, clique em **"+ Add URI"** e cole
   exatamente:
   ```
   https://developers.google.com/oauthplayground
   ```
6. Clique em **"Create"**.
7. Vai aparecer uma janela com **"Your Client ID"** e **"Your Client
   Secret"**. **Copie os dois agora** e cole num lugar temporário (bloco
   de notas) — você vai precisar deles em 2 minutos, na Parte 5, e de
   novo na Parte 6 pra colar como secret do GitHub.

## Parte 5 — Gerar o Refresh Token (OAuth Playground)

1. Acesse **developers.google.com/oauthplayground**.
2. Clique no ícone de **engrenagem ⚙️** no canto superior direito.
3. Marque a caixa **"Use your own OAuth credentials"**.
4. Cole o **Client ID** e o **Client Secret** da Parte 4 nos campos que
   aparecerem.
5. Feche o painel de configurações (clique na engrenagem de novo ou em
   qualquer lugar fora do painel).
6. No painel da esquerda ("Step 1 - Select & authorize APIs"), na caixa
   de busca, cole exatamente:
   ```
   https://www.googleapis.com/auth/gmail.readonly
   ```
   e clique no botão **"Authorize APIs"** (azul, mais abaixo).
7. Você vai ser levado pra tela de login do Google — entre com a mesma
   conta que recebe as notas da Rico. Provavelmente vai aparecer um aviso
   **"Google hasn't verified this app"** — isso é esperado (o app é seu,
   só que ainda não foi revisado pelo Google). Clique em **"Advanced"**
   (ou "Continue"), depois em **"Go to Monitor Carteira (unsafe)"**, e em
   seguida **"Continue"**/**"Allow"** para conceder a permissão de
   leitura do Gmail.
8. Você volta pro OAuth Playground, agora na "Step 2 - Exchange
   authorization code for tokens". Clique no botão azul **"Exchange
   authorization code for tokens"**.
9. Vai aparecer, à direita, um bloco com **"Refresh token"** e "Access
   token". **Copie o valor de "Refresh token"** — é uma string longa. Esse
   é o `GMAIL_REFRESH_TOKEN`.

## Parte 6 — Cadastrar os 4 secrets no GitHub

No repositório `monitor-carteira-limites`, vá em **Settings > Secrets and
variables > Actions**, clique em **"New repository secret"** e cadastre,
um de cada vez:

| Nome do secret | Valor |
|---|---|
| `GMAIL_CLIENT_ID` | o Client ID da Parte 4 |
| `GMAIL_CLIENT_SECRET` | o Client Secret da Parte 4 |
| `GMAIL_REFRESH_TOKEN` | o Refresh token da Parte 5 |
| `NOTA_PDF_SENHA` | os 3 últimos dígitos do seu CPF (a senha que você já usa pra abrir os PDFs das notas) |

## Pronto — como testar

Depois de cadastrar os 4 secrets, vá na aba **Actions** do repositório,
clique no workflow **"Monitor de Carteira"** e depois em **"Run
workflow"** (botão à direita) para forçar uma execução manual. Abra o log
do step **"Importar notas de negociação por e-mail (se configurado)"** —
se tudo estiver certo, ele vai dizer "Nenhuma nota nova" (se não tiver
nota pendente) ou listar as transações importadas.

Se der erro, me manda a mensagem do log — eu ajudo a diagnosticar.

---

## Nota sobre o modo "Testing" (7 dias)

Enquanto o app estiver em modo "Testing" (o que ele está, seguindo só os
passos acima), o Refresh Token pode parar de funcionar depois de 7 dias
sem uso, ou o Google pode pedir reautorização periodicamente — nesse
caso, o step de importação simplesmente falha (sem afetar o resto do
workflow, graças ao `continue-on-error`) e você repete a Parte 5 pra
gerar um Refresh Token novo. Quando quiser eliminar essa manutenção
semanal de vez, me avise — aí seguimos para publicar o app (Parte 3,
botão "Publish App"), o que exige uma página de política de privacidade e
passar pela revisão do Google.
