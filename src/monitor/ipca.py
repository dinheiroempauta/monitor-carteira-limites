"""Cliente da API do Banco Central (SGS) para o IPCA — usado pra calcular
performance real (descontada a inflação). Série 433, mensal, gratuita e
sem necessidade de token (https://dadosabertos.bcb.gov.br/).
"""
from __future__ import annotations

from datetime import date

import requests

IPCA_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.433/dados"


class IpcaFetchError(RuntimeError):
    pass


def fetch_ipca_monthly(start: date, end: date) -> list[tuple[date, float]]:
    """Retorna [(data_do_mês, variação_mensal_%)] entre `start` e `end`
    (inclusive), na ordem cronológica. A variação vem em % ao mês (ex.:
    0.42 significa 0.42%, não 42%)."""
    params = {
        "formato": "json",
        "dataInicial": start.strftime("%d/%m/%Y"),
        "dataFinal": end.strftime("%d/%m/%Y"),
    }
    try:
        response = requests.get(IPCA_URL, params=params, timeout=15)
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        raise IpcaFetchError(f"Falha ao consultar a API do Banco Central (IPCA): {exc}") from exc

    return [(date(*reversed([int(p) for p in item["data"].split("/")])), float(item["valor"])) for item in payload]


def accumulated_index(monthly_variations: list[tuple[date, float]]) -> float:
    """Índice acumulado (ex.: 1.0234 = +2.34% acumulado) a partir de uma
    lista de variações mensais em %."""
    index = 1.0
    for _, variacao_pct in monthly_variations:
        index *= 1 + variacao_pct / 100
    return index
