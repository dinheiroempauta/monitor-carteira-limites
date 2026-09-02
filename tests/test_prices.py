import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from monitor import prices


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


def _ts(y, m, d):
    return int(datetime(y, m, d, tzinfo=timezone.utc).timestamp())


def test_fetch_historical_prices_faz_parse_do_historico_por_dia(monkeypatch):
    payload = {
        "results": [
            {
                "symbol": "B5P211",
                "historicalDataPrice": [
                    {"date": _ts(2026, 8, 4), "close": 109.55},
                    {"date": _ts(2026, 8, 5), "close": 109.66},
                ],
            }
        ]
    }

    calls = []

    def fake_get(url, params, timeout):
        calls.append(params)
        return _FakeResponse(payload)

    monkeypatch.setattr(prices.requests, "get", fake_get)

    result = prices.fetch_historical_prices(["B5P211"], "token", range_="6mo")

    assert result == {"B5P211": {"2026-08-04": 109.55, "2026-08-05": 109.66}}
    assert calls[0]["range"] == "6mo"
    assert calls[0]["interval"] == "1d"


def test_fetch_historical_prices_propaga_erro_quando_ticker_nao_encontrado(monkeypatch):
    def fake_get(url, params, timeout):
        return _FakeResponse({"results": []})

    monkeypatch.setattr(prices.requests, "get", fake_get)

    try:
        prices.fetch_historical_prices(["ZZZZ11"], "token")
        assert False, "deveria ter levantado PriceFetchError"
    except prices.PriceFetchError:
        pass


def test_fetch_prices_tenta_novamente_apos_timeout_transitorio(monkeypatch):
    payload = {"results": [{"symbol": "VWRA11", "regularMarketPrice": 110.77}]}
    calls = []

    def fake_get(url, params, timeout):
        calls.append(params)
        if len(calls) < 2:
            raise prices.requests.exceptions.ReadTimeout("read timeout")
        return _FakeResponse(payload)

    monkeypatch.setattr(prices.requests, "get", fake_get)
    monkeypatch.setattr(prices.time, "sleep", lambda _seconds: None)

    result = prices.fetch_prices(["VWRA11"], "token")

    assert result == {"VWRA11": 110.77}
    assert len(calls) == 2


def test_fetch_prices_propaga_erro_apos_esgotar_tentativas(monkeypatch):
    def fake_get(url, params, timeout):
        raise prices.requests.exceptions.ReadTimeout("read timeout")

    monkeypatch.setattr(prices.requests, "get", fake_get)
    monkeypatch.setattr(prices.time, "sleep", lambda _seconds: None)

    try:
        prices.fetch_prices(["VWRA11"], "token")
        assert False, "deveria ter levantado PriceFetchError"
    except prices.PriceFetchError:
        pass
