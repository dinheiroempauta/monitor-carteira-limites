"""Cliente da API brapi.dev (https://brapi.dev/docs) para cotações da B3.

Trocamos da HG Brasil para a brapi.dev: testamos em produção e a chave HG
Brasil do usuário não tem acesso ao endpoint de cotação (stock_price) em
nenhum ticker, nem mesmo ações líquidas como PETR4 — só no plano Member
Premium ou superior. A brapi.dev tem plano gratuito com 15 mil
requisições/mês (temos de sobra rodando 1x/dia) e cobre FIIs/ETFs
normalmente — mas, no plano free, cada ticker é uma requisição separada
(sem consulta em lote), por isso uma chamada por ativo.
"""
from __future__ import annotations

from datetime import datetime, timezone

import requests

BRAPI_URL = "https://brapi.dev/api/quote/{ticker}"


class PriceFetchError(RuntimeError):
    pass


def _fetch_one(ticker: str, api_key: str) -> float:
    url = BRAPI_URL.format(ticker=ticker)
    try:
        response = requests.get(url, params={"token": api_key}, timeout=15)
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        raise PriceFetchError(f"Falha ao consultar a API brapi.dev para {ticker}: {exc}") from exc

    if payload.get("error"):
        raise PriceFetchError(f"Erro da API brapi.dev para {ticker}: {payload.get('message', payload)!r}")

    results = payload.get("results", [])
    entry = next((r for r in results if isinstance(r, dict) and r.get("symbol", "").upper() == ticker.upper()), None)

    if not entry or entry.get("regularMarketPrice") is None:
        raise PriceFetchError(f"Não foi possível obter cotação para {ticker}. Resposta bruta da API: {payload!r}")

    return float(entry["regularMarketPrice"])


def fetch_prices(tickers: list[str], api_key: str) -> dict[str, float]:
    """Retorna {ticker: preço_atual}, uma chamada por ticker (veja _fetch_one)."""
    return {ticker: _fetch_one(ticker, api_key) for ticker in tickers}


def _fetch_one_historical(ticker: str, api_key: str, range_: str) -> dict[str, float]:
    """Retorna {'YYYY-MM-DD': preço_de_fechamento} para um ticker, usando o
    parâmetro `range` da brapi.dev (histórico incluído no mesmo endpoint de
    cotação, sem custo extra de requisição)."""
    url = BRAPI_URL.format(ticker=ticker)
    try:
        response = requests.get(
            url,
            params={"token": api_key, "range": range_, "interval": "1d"},
            timeout=15,
        )
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        raise PriceFetchError(f"Falha ao consultar histórico da brapi.dev para {ticker}: {exc}") from exc

    if payload.get("error"):
        raise PriceFetchError(f"Erro da API brapi.dev para {ticker}: {payload.get('message', payload)!r}")

    results = payload.get("results", [])
    entry = next((r for r in results if isinstance(r, dict) and r.get("symbol", "").upper() == ticker.upper()), None)
    if not entry:
        raise PriceFetchError(f"Não foi possível obter histórico para {ticker}. Resposta bruta da API: {payload!r}")

    historical = entry.get("historicalDataPrice") or []
    prices: dict[str, float] = {}
    for point in historical:
        close = point.get("close")
        timestamp = point.get("date")
        if close is None or timestamp is None:
            continue
        day = datetime.fromtimestamp(timestamp, tz=timezone.utc).date().isoformat()
        prices[day] = float(close)
    return prices


def fetch_historical_prices(tickers: list[str], api_key: str, range_: str = "5y") -> dict[str, dict[str, float]]:
    """Retorna {ticker: {'YYYY-MM-DD': preço_de_fechamento}}, uma chamada por
    ticker. `range_` segue os valores aceitos pela brapi.dev (1mo, 3mo, 6mo,
    1y, 2y, 5y, 10y, max) — usar o menor range que cubra o histórico
    necessário evita desperdiçar cota da API gratuita."""
    return {ticker: _fetch_one_historical(ticker, api_key, range_) for ticker in tickers}
