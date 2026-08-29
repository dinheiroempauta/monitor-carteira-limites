"""Importa transações a partir das notas de negociação da Rico recebidas
por e-mail (Gmail API) — substitui o registro manual/via formulário.

Roda dentro do GitHub Actions usando um refresh token OAuth do Gmail
(secrets GMAIL_CLIENT_ID/GMAIL_CLIENT_SECRET/GMAIL_REFRESH_TOKEN) e a
senha do PDF (secret NOTA_PDF_SENHA, os 3 últimos dígitos do CPF).

Se os secrets do Gmail ainda não estiverem configurados, este script sai
silenciosamente (exit 0) sem afetar o resto do workflow — ver
specs/003-importacao-automatica-notas/. Nunca commita dados de uma nota
que não conseguiu processar com segurança (senha errada, PDF corrompido,
produto não mapeado): nesse caso, pula só aquela nota, reporta no log e
manda um alerta no Telegram (uma vez só por nota — ver NOTAS_ALERTADAS_PATH),
deixando para a próxima execução tentar de novo.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from monitor.notas_rico import (  # noqa: E402
    ProdutoNaoMapeado,
    decode_raw_email,
    extract_pdf_attachment,
    linhas_nao_reconhecidas,
    parse_nota_pdf,
    transaction_csv_line,
)
from monitor.telegram import TelegramSendError, send_message  # noqa: E402
from monitor.transactions import TRANSACTIONS_PATH  # noqa: E402

PROCESSED_NOTAS_PATH = REPO_ROOT / "config" / "processed_notas.txt"
# Notas que falharam ao importar (produto não mapeado, zero operações
# reconhecidas, erro genérico) NÃO entram em processed_notas.txt de
# propósito — a ideia é tentar de novo na próxima execução, caso o
# problema seja transitório. Mas isso sozinho faria o mesmo alerta repetir
# a cada execução (a cada 15min) enquanto ninguém resolver a causa — este
# arquivo separado registra só "já avisei sobre essa nota", pra mandar o
# alerta no Telegram uma vez só por nota problemática.
NOTAS_ALERTADAS_PATH = REPO_ROOT / "config" / "notas_com_problema.txt"

GMAIL_QUERY = 'from:noreply@rico.com.vc subject:"Nota de Negociação"'
GMAIL_API = "https://www.googleapis.com/gmail/v1/users/me"
TOKEN_URL = "https://oauth2.googleapis.com/token"


def get_access_token(client_id: str, client_secret: str, refresh_token: str) -> str:
    resp = requests.post(
        TOKEN_URL,
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def search_message_ids(token: str) -> list[str]:
    resp = requests.get(
        f"{GMAIL_API}/messages",
        headers={"Authorization": f"Bearer {token}"},
        params={"q": GMAIL_QUERY},
        timeout=30,
    )
    resp.raise_for_status()
    return [m["id"] for m in resp.json().get("messages", [])]


def get_raw_message(token: str, message_id: str) -> str:
    resp = requests.get(
        f"{GMAIL_API}/messages/{message_id}",
        headers={"Authorization": f"Bearer {token}"},
        params={"format": "raw"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["raw"]


def load_processed_ids() -> set[str]:
    if not PROCESSED_NOTAS_PATH.exists():
        return set()
    return {line.strip() for line in PROCESSED_NOTAS_PATH.read_text(encoding="utf-8").splitlines() if line.strip()}


def load_alerted_ids() -> set[str]:
    if not NOTAS_ALERTADAS_PATH.exists():
        return set()
    return {line.strip() for line in NOTAS_ALERTADAS_PATH.read_text(encoding="utf-8").splitlines() if line.strip()}


def main() -> int:
    client_id = os.environ.get("GMAIL_CLIENT_ID")
    client_secret = os.environ.get("GMAIL_CLIENT_SECRET")
    refresh_token = os.environ.get("GMAIL_REFRESH_TOKEN")
    senha_pdf = os.environ.get("NOTA_PDF_SENHA")

    if not all([client_id, client_secret, refresh_token, senha_pdf]):
        print("Importação de notas por e-mail: secrets do Gmail ainda não configurados — pulando (ver specs/003).")
        return 0

    token = get_access_token(client_id, client_secret, refresh_token)
    message_ids = search_message_ids(token)

    processed = load_processed_ids()
    new_ids = [m for m in message_ids if m not in processed]
    if not new_ids:
        print("Nenhuma nota nova.")
        return 0

    # Processa da mais antiga para a mais nova (a API do Gmail devolve mais recente primeiro).
    new_ids.reverse()

    alerted = load_alerted_ids()

    new_lines: list[str] = []
    newly_processed: list[str] = []
    resumo: list[str] = []
    problemas: list[tuple[str, str]] = []  # (message_id, descrição)

    for message_id in new_ids:
        try:
            raw_b64url = get_raw_message(token, message_id)
            raw_bytes = decode_raw_email(raw_b64url)
            pdf_bytes = extract_pdf_attachment(raw_bytes)
            operacoes = parse_nota_pdf(pdf_bytes, senha_pdf)
        except ProdutoNaoMapeado as exc:
            print(f"AVISO: nota {message_id} tem produto não mapeado ({exc.produto!r}) — pulando, não lançada.")
            problemas.append((message_id, f"nota {message_id}: produto não mapeado ({exc.produto!r})"))
            continue
        except Exception as exc:  # noqa: BLE001 — nunca commitar dado incerto; loga e segue
            print(f"AVISO: falha ao processar nota {message_id} ({exc}) — pulando, não lançada.")
            problemas.append((message_id, f"nota {message_id}: falha ao processar ({exc})"))
            continue

        if not operacoes:
            print(f"AVISO: nota {message_id} não teve nenhuma operação reconhecida — pulando.")
            try:
                suspeitas = linhas_nao_reconhecidas(pdf_bytes, senha_pdf)
            except Exception as exc:  # noqa: BLE001 — diagnóstico é best-effort, não pode quebrar o import
                suspeitas = []
                print(f"  (não foi possível gerar diagnóstico: {exc})")
            for linha in suspeitas:
                print(f"  linha não reconhecida: {linha}")
            detalhe = f" — linha(s): {' | '.join(suspeitas)}" if suspeitas else " (sem linha de operação identificável)"
            problemas.append((message_id, f"nota {message_id}: zero operações reconhecidas{detalhe}"))
            continue

        for op in operacoes:
            new_lines.append(transaction_csv_line(op))
            resumo.append(f"{op['date']} {op['ticker']} {op['action']} {op['qty']}x @ R$ {op['price']:.2f}")
        newly_processed.append(message_id)

    problemas_novos = [(mid, desc) for mid, desc in problemas if mid not in alerted]
    if problemas_novos:
        bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
        chat_id = os.environ.get("TELEGRAM_CHAT_ID")
        if bot_token and chat_id:
            texto = "⚠️ Nota(s) de negociação não reconhecida(s) automaticamente:\n\n" + "\n".join(
                f"◾ {desc}" for _, desc in problemas_novos
            )
            try:
                send_message(texto, bot_token, chat_id)
            except TelegramSendError as exc:
                print(f"Falha ao alertar sobre nota(s) não reconhecida(s): {exc}", file=sys.stderr)
        with NOTAS_ALERTADAS_PATH.open("a", encoding="utf-8") as f:
            for mid, _ in problemas_novos:
                f.write(mid + "\n")

    if not new_lines:
        print("Nenhuma transação nova lançada nesta execução.")
        return 0

    with TRANSACTIONS_PATH.open("a", encoding="utf-8") as f:
        for line in new_lines:
            f.write(line + "\n")

    with PROCESSED_NOTAS_PATH.open("a", encoding="utf-8") as f:
        for message_id in newly_processed:
            f.write(message_id + "\n")

    print(f"Importadas {len(new_lines)} transação(ões) de {len(newly_processed)} nota(s):")
    for linha in resumo:
        print(f"  - {linha}")

    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a", encoding="utf-8") as f:
            f.write("notas_importadas<<__NOTAS_EOF__\n")
            for linha in resumo:
                f.write(linha + "\n")
            f.write("__NOTAS_EOF__\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
