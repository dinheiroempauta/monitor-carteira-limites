import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from monitor import historical_prices as hp


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


def test_fetch_historical_prices_faz_parse_com_timestamp_unix(monkeypatch):
    payload = {
        "results": [
            {
                "symbol": "VWRA11",
                "historicalDataPrice": [
                    {"date": 1735689600, "close": 100.0},  # 2025-01-01 UTC
                    {"date": 1735776000, "close": 101.5},  # 2025-01-02 UTC
                ],
            }
        ]
    }

    def fake_get(url, params, timeout):
        return _FakeResponse(payload)

    monkeypatch.setattr(hp.requests, "get", fake_get)

    result = hp.fetch_historical_prices("VWRA11", "fake-token")
    assert result == [(date(2025, 1, 1), 100.0), (date(2025, 1, 2), 101.5)]


def test_fetch_historical_prices_faz_parse_com_data_iso(monkeypatch):
    payload = {
        "results": [
            {
                "symbol": "B5P211",
                "historicalDataPrice": [{"date": "2025-01-01T00:00:00.000Z", "close": 105.2}],
            }
        ]
    }

    def fake_get(url, params, timeout):
        return _FakeResponse(payload)

    monkeypatch.setattr(hp.requests, "get", fake_get)

    result = hp.fetch_historical_prices("B5P211", "fake-token")
    assert result == [(date(2025, 1, 1), 105.2)]


def test_fetch_historical_prices_sem_historico_da_erro_com_payload_bruto(monkeypatch):
    payload = {"results": [{"symbol": "GOLD11", "historicalDataPrice": []}]}

    def fake_get(url, params, timeout):
        return _FakeResponse(payload)

    monkeypatch.setattr(hp.requests, "get", fake_get)

    try:
        hp.fetch_historical_prices("GOLD11", "fake-token")
        assert False, "deveria ter levantado HistoricalPriceFetchError"
    except hp.HistoricalPriceFetchError as exc:
        assert "GOLD11" in str(exc)
