import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from monitor.performance import compute_performance, compute_wealth_series
from monitor.transactions import Transaction

TRANSACTIONS = [
    Transaction(date(2026, 1, 1), "B5P211", "compra", 10, 100.0),  # investe 1000
]

PRICE_HISTORY = {
    "B5P211": [
        (date(2026, 1, 1), 100.0),
        (date(2026, 2, 1), 110.0),
        (date(2026, 3, 1), 121.0),
    ]
}


def test_compute_wealth_series_usa_ultimo_preco_conhecido():
    dates = [date(2026, 1, 1), date(2026, 1, 15), date(2026, 2, 1), date(2026, 3, 1)]
    series = compute_wealth_series(TRANSACTIONS, PRICE_HISTORY, dates)
    series_by_date = dict(series)
    assert series_by_date[date(2026, 1, 1)] == 1000.0
    # 1/15 não tem preço novo — usa o último conhecido (1/1 = 100)
    assert series_by_date[date(2026, 1, 15)] == 1000.0
    assert series_by_date[date(2026, 2, 1)] == 1100.0
    assert series_by_date[date(2026, 3, 1)] == 1210.0


def test_compute_wealth_series_antes_da_primeira_transacao_e_zero():
    series = compute_wealth_series(TRANSACTIONS, PRICE_HISTORY, [date(2025, 12, 1)])
    assert series == [(date(2025, 12, 1), 0.0)]


def test_compute_performance_nominal_sem_ipca():
    wealth_series = compute_wealth_series(TRANSACTIONS, PRICE_HISTORY, [date(2026, 1, 1), date(2026, 3, 1)])
    points = compute_performance(TRANSACTIONS, wealth_series, ipca_monthly=[])
    by_date = {p.date: p for p in points}
    assert by_date[date(2026, 1, 1)].nominal_return == 0.0
    assert abs(by_date[date(2026, 3, 1)].nominal_return - 0.21) < 1e-9  # 1210/1000 - 1
    assert by_date[date(2026, 3, 1)].real_return is None  # sem dado de IPCA


def test_compute_performance_real_desconta_inflacao():
    wealth_series = compute_wealth_series(TRANSACTIONS, PRICE_HISTORY, [date(2026, 3, 1)])
    ipca_monthly = [(date(2026, 1, 1), 1.0), (date(2026, 2, 1), 1.0), (date(2026, 3, 1), 1.0)]
    points = compute_performance(TRANSACTIONS, wealth_series, ipca_monthly)
    p = points[0]
    # nominal = 0.21; indice ipca acumulado = 1.01^3
    indice = 1.01**3
    esperado_real = (1.21) / indice - 1
    assert abs(p.real_return - esperado_real) < 1e-9


def test_compute_performance_sem_transacoes_retorna_vazio():
    assert compute_performance([], [], []) == []
