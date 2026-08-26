"""Notifica no Telegram, logo após uma (ou mais) nota(s) de negociação
nova(s) ser(em) importada(s) por e-mail, quais operações entraram e como
ficou a posição atual — independente de ter havido mudança de banda (esse
é o critério do monitor.main; aqui o gatilho é só "teve nota nova").

Chamado pelo monitor.yml só quando o step de importação de notas produziu
o output `notas_importadas` (não vazio).
"""
from __future__ import annotations

import os
import sys

from monitor.allocation import compute_statuses, rebalance_plan
from monitor.config import load_portfolio, load_quotas, load_quotas_metadata
from monitor.prices import PriceFetchError, fetch_prices
from monitor.report import build_report
from monitor.telegram import TelegramSendError, send_message


def main() -> int:
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    brapi_token = os.environ.get("BRAPI_TOKEN")
    resumo = os.environ.get("NOTAS_IMPORTADAS_RESUMO", "").strip()

    if not (bot_token and chat_id):
        print("Telegram não configurado — pulando notificação de nota importada.", file=sys.stderr)
        return 0
    if not resumo:
        print("Nenhum resumo de nota importada recebido — nada a notificar.", file=sys.stderr)
        return 0
    if not brapi_token:
        print("BRAPI_TOKEN não configurado — não é possível calcular a posição atual.", file=sys.stderr)
        return 1

    try:
        targets = load_portfolio()
        holdings = load_quotas()
        quotas_metadata = load_quotas_metadata()
        prices = fetch_prices(list(targets.keys()), brapi_token)
        statuses = compute_statuses(holdings, prices, targets)
    except PriceFetchError as exc:
        print(f"Erro ao buscar cotações: {exc}", file=sys.stderr)
        return 1

    actions = rebalance_plan(statuses)
    posicao = build_report(statuses, actions, quotas_metadata, show_values=True)

    mensagem = "📥 *Nota(s) de negociação importada(s)*\n\n" + resumo + "\n\n" + posicao

    try:
        send_message(mensagem, bot_token, chat_id, parse_mode="Markdown")
    except TelegramSendError as exc:
        print(f"\n{exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
