"""Entrypoint: carrega config, busca preços, calcula alocação e notifica.

Roda com frequência (ex.: a cada 30min via cron), mas só envia mensagem no
Telegram quando o status de banda de algum ativo muda em relação à última
vez que alertamos (com uma margem de histerese pra não oscilar perto da
borda) — evita inflar o chat com uma mensagem por execução. Qualquer falha
inesperada também vira um alerta no Telegram, pra não passar batido.
"""
from __future__ import annotations

import os
import sys
import traceback

from monitor.allocation import compute_statuses, effective_status_for_alerting, rebalance_plan
from monitor.config import (
    append_history,
    load_last_status,
    load_portfolio,
    load_quotas,
    load_quotas_metadata,
    save_last_status,
)
from monitor.prices import PriceFetchError, fetch_prices
from monitor.report import build_report
from monitor.telegram import TelegramSendError, send_message


def _notify_failure(bot_token: str | None, chat_id: str | None, erro: str) -> None:
    """Best-effort: uma falha no monitor não deve passar em silêncio."""
    if not (bot_token and chat_id):
        return
    try:
        send_message(f"🔴 *Monitor de Carteira falhou*\n\n{erro}", bot_token, chat_id)
    except TelegramSendError:
        pass  # já estamos no caminho de erro; não há mais o que fazer aqui


def main() -> int:
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    brapi_token = os.environ.get("BRAPI_TOKEN")
    if not brapi_token:
        erro = "Erro: variável de ambiente BRAPI_TOKEN não configurada."
        print(erro, file=sys.stderr)
        _notify_failure(bot_token, chat_id, erro)
        return 1

    try:
        targets = load_portfolio()
        holdings = load_quotas()
        quotas_metadata = load_quotas_metadata()
        prices = fetch_prices(list(targets.keys()), brapi_token)
        statuses = compute_statuses(holdings, prices, targets)
    except PriceFetchError as exc:
        erro = f"Erro ao buscar cotações: {exc}"
        print(erro, file=sys.stderr)
        _notify_failure(bot_token, chat_id, erro)
        return 1
    except Exception as exc:  # config inválida, YAML quebrado, etc. — nunca falhar em silêncio
        erro = f"Erro inesperado: {exc}"
        print(erro, file=sys.stderr)
        print(traceback.format_exc(), file=sys.stderr)
        _notify_failure(bot_token, chat_id, erro)
        return 1

    actions = rebalance_plan(statuses)

    log_report = build_report(statuses, actions, quotas_metadata, show_values=True)
    print(log_report)

    last_status = load_last_status()
    effective_status = effective_status_for_alerting(statuses, last_status)
    status_changed = effective_status != last_status

    if not status_changed:
        print("\n(Status de banda sem mudança desde o último alerta — Telegram não acionado.)", file=sys.stderr)
        return 0

    telegram_report = build_report(statuses, actions, quotas_metadata, show_values=False)
    if bot_token and chat_id:
        try:
            send_message(telegram_report, bot_token, chat_id, parse_mode="Markdown")
        except TelegramSendError as exc:
            print(f"\n{exc}", file=sys.stderr)
            return 1
    else:
        print("\n(Telegram não configurado — relatório impresso apenas no log.)", file=sys.stderr)

    save_last_status(effective_status)
    append_history({s.ticker: s.pct for s in statuses})
    return 0


if __name__ == "__main__":
    sys.exit(main())
