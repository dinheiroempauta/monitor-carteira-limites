"""Entrypoint: carrega config, busca preços, calcula alocação e notifica."""
from __future__ import annotations

import os
import sys

from monitor.allocation import compute_statuses, contribution_suggestion, rebalance_plan
from monitor.config import load_portfolio, load_quotas, load_quotas_metadata
from monitor.prices import PriceFetchError, fetch_prices
from monitor.report import build_report
from monitor.telegram import TelegramSendError, send_message


def main() -> int:
    brapi_token = os.environ.get("BRAPI_TOKEN")
    if not brapi_token:
        print("Erro: variável de ambiente BRAPI_TOKEN não configurada.", file=sys.stderr)
        return 1

    targets = load_portfolio()
    holdings = load_quotas()
    quotas_metadata = load_quotas_metadata()

    try:
        prices = fetch_prices(list(targets.keys()), brapi_token)
    except PriceFetchError as exc:
        print(f"Erro ao buscar cotações: {exc}", file=sys.stderr)
        return 1

    statuses = compute_statuses(holdings, prices, targets)
    actions = rebalance_plan(statuses)
    contribution_weights = contribution_suggestion(statuses)

    report = build_report(statuses, actions, contribution_weights, quotas_metadata)
    print(report)

    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if bot_token and chat_id:
        try:
            send_message(report, bot_token, chat_id)
        except TelegramSendError as exc:
            print(f"\n{exc}", file=sys.stderr)
            return 1
    else:
        print("\n(Telegram não configurado — relatório impresso apenas no log.)", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
