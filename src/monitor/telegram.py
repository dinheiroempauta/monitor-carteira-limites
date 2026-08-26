"""Envio de mensagem via Telegram Bot API."""
from __future__ import annotations

import requests


class TelegramSendError(RuntimeError):
    pass


def send_message(text: str, bot_token: str, chat_id: str, parse_mode: str | None = None) -> None:
    """`parse_mode="Markdown"` só deve ser usado com texto 100% controlado
    por nós (sem trecho de exceção/erro embutido) — um `*` ou `_` sem par
    nesse texto faz a API do Telegram recusar a mensagem inteira (erro
    "can't parse entities"), o que é especialmente ruim em uma mensagem de
    alerta de falha."""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    if parse_mode:
        payload["parse_mode"] = parse_mode
    try:
        response = requests.post(url, json=payload, timeout=15)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise TelegramSendError(f"Falha ao enviar mensagem no Telegram: {exc}") from exc
