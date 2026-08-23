"""Cliente da API brapi.dev (https://brapi.dev/docs) para cotações da B3.

Trocamos da HG Brasil para a brapi.dev: testamos em produção e a chave HG
Brasil do usuário não tem acesso ao endpoint de cotação (stock_price) em
nenhum ticker, nem mesmo ações líquidas como PETR4 — só no plano Member
Premium ou superior. A brapi.dev tem plano gratuito com 15 mil requisições
por mês (temos de sobra rodando 1x/dia) e cobre FIIs/ETFs normalmente.
"""
from __future__ import annotations

import requests

BRAPI_URL = "https://brapi.dev/api/quote/{tickers}"


class PriceFetchError(RuntimeError):
    pass


def fetch_prices(tickers: list[str], api_key: str) -> dict[str, float]:
    """Retorna {ticker: preço_atual} para os tickers informados."""
    url = BRAPI_URL.format(tickers=",".join(tickers))
    try:
        response = requests.get(url, params={"token": api_key}, timeout=15)
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        raise PriceFetchError(f"Falha ao consultar a API brapi.dev: {exc}") from exc

    if payload.get("error"):
        raise PriceFetchError(f"Erro da API brapi.dev: {payload.get('message', payload)!r}")

    results = payload.get("results", [])
    by_symbol = {entry.get("symbol", "").upper(): entry for entry in results if isinstance(entry, dict)}

    prices: dict[str, float] = {}
    missing: list[str] = []
    for ticker in tickers:
        entry = by_symbol.get(ticker.upper())
        if not entry or entry.get("regularMarketPrice") is None:
            missing.append(ticker)
            continue
        prices[ticker] = float(entry["regularMarketPrice"])

    if missing:
        raise PriceFetchError(
            f"Não foi possível obter cotação para: {', '.join(missing)}. Resposta bruta da API: {payload!r}"
        )

    return prices
