import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

_spec = importlib.util.spec_from_file_location("calcular_aporte", REPO_ROOT / "scripts" / "calcular_aporte.py")
calcular_aporte = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(calcular_aporte)

PRECOS_FIXOS = {"B5P211": 110.64, "VWRA11": 114.67, "DIVO11": 123.69, "CDIB11": 51.57, "GOLD11": 24.83}


def test_sem_aporte_solicitado_nao_chama_nada(monkeypatch, capsys):
    monkeypatch.delenv("APORTE_VALOR", raising=False)

    def _falha(*args, **kwargs):
        raise AssertionError("não deveria buscar cotação nem mandar mensagem sem aporte solicitado")

    monkeypatch.setattr(calcular_aporte, "fetch_prices", _falha)
    monkeypatch.setattr(calcular_aporte, "send_message", _falha)

    assert calcular_aporte.main() == 0
    assert "pulando" in capsys.readouterr().out


def test_valor_invalido_notifica_erro_no_telegram(monkeypatch):
    monkeypatch.setenv("APORTE_VALOR", "não é um número")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token-fake")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat-fake")

    enviado = {}

    def _capturar_send(texto, bot_token, chat_id):
        enviado["texto"] = texto

    monkeypatch.setattr(calcular_aporte, "send_message", _capturar_send)

    assert calcular_aporte.main() == 1
    assert "inválido" in enviado["texto"]


def test_fluxo_feliz_calcula_e_manda_relatorio_no_telegram(monkeypatch):
    monkeypatch.setenv("APORTE_VALOR", "4770.13")
    monkeypatch.setenv("BRAPI_TOKEN", "token-fake")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token-fake")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat-fake")

    monkeypatch.setattr(calcular_aporte, "fetch_prices", lambda tickers, api_key: dict(PRECOS_FIXOS))

    enviado = {}

    def _capturar_send(texto, bot_token, chat_id):
        enviado["texto"] = texto

    monkeypatch.setattr(calcular_aporte, "send_message", _capturar_send)

    assert calcular_aporte.main() == 0
    assert "4,770.13" in enviado["texto"]
    for ticker in PRECOS_FIXOS:
        assert ticker in enviado["texto"]
