"""Calcula a distribuição de um aporte e manda o resultado no Telegram —
pensado para ser disparado por um `workflow_dispatch` do monitor.yml com o
campo de entrada `aporte` preenchido, direto pela interface do GitHub
(site ou app), sem precisar de terminal, script local, nem nenhum agente
de codificação no caminho.

Busca a cotação de novo (uma chamada por ativo à brapi.dev, plano free
tem folga de sobra pra isso) em vez de reaproveitar a do passo "Rodar
monitor e notificar" — cada step do workflow é um processo Python
separado, então não há estado compartilhado entre eles sem escrever em
arquivo, e uma chamada a mais por aporte não custa nada.

Se a variável de ambiente APORTE_VALOR estiver vazia (execução agendada
normal, sem ninguém pedindo aporte), sai silenciosamente sem fazer nada.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from monitor.allocation import aporte_quotas_plan, compute_statuses  # noqa: E402
from monitor.config import load_portfolio, load_quotas  # noqa: E402
from monitor.prices import PriceFetchError, fetch_prices  # noqa: E402
from monitor.report import build_aporte_report  # noqa: E402
from monitor.telegram import TelegramSendError, send_message  # noqa: E402


def main() -> int:
    aporte_valor = os.environ.get("APORTE_VALOR", "").strip()
    if not aporte_valor:
        print("Nenhum aporte solicitado nesta execução (campo 'aporte' vazio) — pulando.")
        return 0

    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    brapi_token = os.environ.get("BRAPI_TOKEN")

    def notificar_erro(mensagem: str) -> None:
        print(mensagem, file=sys.stderr)
        if bot_token and chat_id:
            try:
                send_message(f"🔴 *Cálculo de aporte falhou*\n\n{mensagem}", bot_token, chat_id)
            except TelegramSendError:
                pass

    try:
        aporte = float(aporte_valor.replace(",", "."))
    except ValueError:
        notificar_erro(f"Valor de aporte inválido: {aporte_valor!r} (use só números, ex.: 4770.13).")
        return 1

    if not brapi_token:
        notificar_erro("BRAPI_TOKEN não configurado — não dá pra buscar cotação.")
        return 1

    try:
        targets = load_portfolio()
        holdings = load_quotas()
        prices = fetch_prices(list(targets.keys()), brapi_token)
    except PriceFetchError as exc:
        notificar_erro(f"Erro ao buscar cotações: {exc}")
        return 1

    statuses = compute_statuses(holdings, prices, targets)
    plan = aporte_quotas_plan(statuses, aporte)
    relatorio = build_aporte_report(plan, statuses, aporte)

    print(relatorio)

    if not (bot_token and chat_id):
        print("\n(Telegram não configurado — relatório impresso apenas no log.)", file=sys.stderr)
        return 0

    try:
        send_message(relatorio, bot_token, chat_id)
    except TelegramSendError as exc:
        print(f"\n{exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
