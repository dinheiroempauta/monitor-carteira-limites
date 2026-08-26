import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from monitor.telegram import send_message


class _RespostaFake:
    def raise_for_status(self):
        pass


def test_send_message_sem_parse_mode_nao_inclui_o_campo(monkeypatch):
    payload_capturado = {}

    def _post_fake(url, json, timeout):
        payload_capturado.update(json)
        return _RespostaFake()

    monkeypatch.setattr("monitor.telegram.requests.post", _post_fake)

    send_message("texto qualquer com *asterisco* solto", "token", "chat")

    assert "parse_mode" not in payload_capturado
    assert payload_capturado["text"] == "texto qualquer com *asterisco* solto"


def test_send_message_com_parse_mode_inclui_o_campo(monkeypatch):
    payload_capturado = {}

    def _post_fake(url, json, timeout):
        payload_capturado.update(json)
        return _RespostaFake()

    monkeypatch.setattr("monitor.telegram.requests.post", _post_fake)

    send_message("*negrito*", "token", "chat", parse_mode="Markdown")

    assert payload_capturado["parse_mode"] == "Markdown"
