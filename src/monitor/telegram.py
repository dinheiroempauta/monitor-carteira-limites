"""Envio de mensagem via Telegram Bot API."""
from __future__ import annotations

import requests


class TelegramSendError(RuntimeError):
    pass


def send_message(text: str, bot_token: str, chat_id: str) -> None:
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    try:
        response = requests.post(url, json={"chat_id": chat_id, "text": text}, timeout=15)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise TelegramSendError(f"Falha ao enviar mensagem no Telegram: {exc}") from exc
