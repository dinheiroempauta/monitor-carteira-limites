"""Calcula as séries de patrimônio e performance (nominal/real) a partir das
transações e do histórico de preços. Funções puras — sem I/O — para serem
fáceis de testar com dados sintéticos.
"""
from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass
from datetime import date

from monitor.ipca import accumulated_index
from monitor.transactions import Transaction, holdings_at, total_invested_at


@dataclass(frozen=True)
class PerformancePoint:
    date: date
    wealth: float
    invested: float
    nominal_return: float  # ex.: 0.05 = +5%
    real_return: float | None  # None se não tiver dado de IPCA pra essa data


def _price_on_or_before(history: list[tuple[date, float]], as_of: date) -> float | None:
    """Último preço conhecido em `history` (ordenado por data) na data ou
    antes dela — "preenche pra frente" nos dias sem pregão/sem dado."""
    dates = [d for d, _ in history]
    idx = bisect_right(dates, as_of) - 1
    if idx < 0:
        return None
    return history[idx][1]


def compute_wealth_series(
    transactions: list[Transaction],
    price_history: dict[str, list[tuple[date, float]]],
    dates: list[date],
) -> list[tuple[date, float]]:
    """Patrimônio total em cada data de `dates` (ordenadas)."""
    series = []
    for d in sorted(dates):
        holdings = holdings_at(transactions, d)
        total = 0.0
        for ticker, qty in holdings.items():
            if qty == 0:
                continue
            preco = _price_on_or_before(price_history.get(ticker, []), d)
            if preco is not None:
                total += qty * preco
        series.append((d, total))
    return series


def compute_performance(
    transactions: list[Transaction],
    wealth_series: list[tuple[date, float]],
    ipca_monthly: list[tuple[date, float]],
) -> list[PerformancePoint]:
    """Combina patrimônio + total investido + IPCA em uma série de
    performance nominal e real."""
    if not transactions:
        return []
    inicio = transactions[0].date

    points = []
    for d, wealth in wealth_series:
        invested = total_invested_at(transactions, d)
        if invested <= 0:
            continue
        nominal = wealth / invested - 1

        variacoes_ate_a_data = [(m, v) for m, v in ipca_monthly if inicio <= m <= d]
        indice = accumulated_index(variacoes_ate_a_data)
        real = (1 + nominal) / indice - 1 if variacoes_ate_a_data else None

        points.append(PerformancePoint(date=d, wealth=wealth, invested=invested, nominal_return=nominal, real_return=real))
    return points
