"""Cliente da API HG Brasil (https://hgbrasil.com/docs/finance/)."""
from __future__ import annotations

import requests

HG_BRASIL_URL = "https://api.hgbrasil.com/finance/stock_price"


class PriceFetchError(RuntimeError):
    pass


def fetch_prices(tickers: list[str], api_key: str) -> dict[str, float]:
    """Retorna {ticker: preço_atual} para os tickers informados."""
    try:
        response = requests.get(
            HG_BRASIL_URL,
            params={"key": api_key, "symbol": ",".join(tickers)},
            timeout=15,
        )
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        raise PriceFetchError(f"Falha ao consultar a API HG Brasil: {exc}") from exc

    if payload.get("valid_key") is False:
        raise PriceFetchError("Chave da API HG Brasil inválida ou expirada.")

    results = payload.get("results", {})
    # A API retorna "results" como dict (chaveado pelo símbolo) em alguns
    # planos/endpoints e como lista de objetos com "symbol" em outros.
    if isinstance(results, list):
        results = {entry.get("symbol", "").upper(): entry for entry in results if isinstance(entry, dict)}

    prices: dict[str, float] = {}
    missing: list[str] = []
    for ticker in tickers:
        entry = results.get(ticker) or results.get(ticker.upper()) or results.get(ticker.lower())
        if not entry or "price" not in entry:
            missing.append(ticker)
            continue
        prices[ticker] = float(entry["price"])

    if missing:
        raise PriceFetchError(
            f"Não foi possível obter cotação para: {', '.join(missing)}. "
            f"Resposta bruta da API: {payload!r}"
        )

    return prices
