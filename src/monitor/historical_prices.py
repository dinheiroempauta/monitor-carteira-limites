"""Cliente do histórico de preços da brapi.dev — usado pra reconstruir o
patrimônio da carteira ao longo do tempo.

Assim como em prices.py, o formato exato da resposta só pode ser confirmado
rodando contra a API de verdade (sem rede neste ambiente de dev). Em caso de
formato inesperado, o erro inclui o payload bruto para facilitar o ajuste —
mesmo padrão que usamos para descobrir o formato certo da brapi.dev antes.
"""
from __future__ import annotations

from datetime import date, datetime

import requests

BRAPI_URL = "https://brapi.dev/api/quote/{ticker}"


class HistoricalPriceFetchError(RuntimeError):
    pass


def fetch_historical_prices(ticker: str, api_key: str, range_: str = "5y") -> list[tuple[date, float]]:
    """Retorna [(data, preço_de_fechamento)] em ordem cronológica."""
    url = BRAPI_URL.format(ticker=ticker)
    try:
        response = requests.get(
            url,
            params={"token": api_key, "range": range_, "interval": "1d"},
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        raise HistoricalPriceFetchError(f"Falha ao consultar histórico de {ticker}: {exc}") from exc

    if payload.get("error"):
        raise HistoricalPriceFetchError(f"Erro da API brapi.dev para histórico de {ticker}: {payload.get('message', payload)!r}")

    results = payload.get("results", [])
    entry = next((r for r in results if isinstance(r, dict) and r.get("symbol", "").upper() == ticker.upper()), None)
    historico = entry.get("historicalDataPrice") if entry else None

    if not historico:
        raise HistoricalPriceFetchError(
            f"Resposta sem histórico de preços para {ticker}. Resposta bruta da API: {payload!r}"
        )

    parsed = []
    for ponto in historico:
        preco = ponto.get("close") if isinstance(ponto, dict) else None
        data_bruta = ponto.get("date") if isinstance(ponto, dict) else None
        if preco is None or data_bruta is None:
            continue
        if isinstance(data_bruta, (int, float)):
            data = datetime.fromtimestamp(data_bruta).date()
        else:
            data = datetime.fromisoformat(str(data_bruta).replace("Z", "+00:00")).date()
        parsed.append((data, float(preco)))

    if not parsed:
        raise HistoricalPriceFetchError(
            f"Não consegui interpretar nenhum ponto do histórico de {ticker}. Resposta bruta: {payload!r}"
        )

    return sorted(parsed, key=lambda p: p[0])
