"""Cliente da API HG Brasil (https://hgbrasil.com/docs/finance/)."""
from __future__ import annotations

import requests

HG_BRASIL_URL = "https://api.hgbrasil.com/finance/stock_price"


class PriceFetchError(RuntimeError):
    pass


def _fetch_one(ticker: str, api_key: str) -> float:
    """Consulta um único símbolo. No plano gratuito, consultar vários
    símbolos separados por vírgula numa mesma chamada exige plano
    Professional/Enterprise — por isso uma chamada por ticker."""
    try:
        response = requests.get(
            HG_BRASIL_URL,
            params={"key": api_key, "symbol": ticker},
            timeout=15,
        )
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        raise PriceFetchError(f"Falha ao consultar a API HG Brasil para {ticker}: {exc}") from exc

    if payload.get("valid_key") is False:
        raise PriceFetchError("Chave da API HG Brasil inválida ou expirada.")

    results = payload.get("results", {})
    if isinstance(results, list):
        results = results[0] if results else {}
    # Para uma única consulta, "results" já é o objeto do ativo; mas alguns
    # planos ainda retornam aninhado por símbolo — tentamos os dois formatos.
    entry = results if "price" in results else (results.get(ticker) or results.get(ticker.upper()) or results.get(ticker.lower()) or {})

    if not entry or "price" not in entry:
        raise PriceFetchError(
            f"Não foi possível obter cotação para {ticker}. Resposta bruta da API: {payload!r}"
        )

    return float(entry["price"])


def fetch_prices(tickers: list[str], api_key: str) -> dict[str, float]:
    """Retorna {ticker: preço_atual} para os tickers informados, uma
    chamada por ticker (veja _fetch_one)."""
    return {ticker: _fetch_one(ticker, api_key) for ticker in tickers}
