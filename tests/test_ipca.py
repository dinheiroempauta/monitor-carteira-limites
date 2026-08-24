import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from monitor import ipca


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


def test_fetch_ipca_monthly_faz_parse_do_payload_da_bcb(monkeypatch):
    payload = [
        {"data": "01/01/2026", "valor": "0.52"},
        {"data": "01/02/2026", "valor": "0.30"},
    ]

    def fake_get(url, params, timeout):
        return _FakeResponse(payload)

    monkeypatch.setattr(ipca.requests, "get", fake_get)

    result = ipca.fetch_ipca_monthly(date(2026, 1, 1), date(2026, 2, 28))
    assert result == [(date(2026, 1, 1), 0.52), (date(2026, 2, 1), 0.30)]


def test_fetch_ipca_monthly_propaga_erro_de_rede(monkeypatch):
    import requests

    def fake_get(url, params, timeout):
        raise requests.RequestException("timeout")

    monkeypatch.setattr(ipca.requests, "get", fake_get)

    try:
        ipca.fetch_ipca_monthly(date(2026, 1, 1), date(2026, 2, 28))
        assert False, "deveria ter levantado IpcaFetchError"
    except ipca.IpcaFetchError:
        pass


def test_accumulated_index_multiplica_variacoes_mensais():
    variacoes = [(date(2026, 1, 1), 1.0), (date(2026, 2, 1), 2.0)]
    # (1.01 * 1.02) = 1.0302
    assert abs(ipca.accumulated_index(variacoes) - 1.0302) < 1e-9


def test_accumulated_index_lista_vazia_retorna_1():
    assert ipca.accumulated_index([]) == 1.0
