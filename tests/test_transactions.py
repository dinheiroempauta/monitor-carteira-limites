import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from monitor.transactions import (
    Transaction,
    current_holdings,
    first_transaction_date,
    holdings_at,
    load_transactions,
    total_invested_at,
)


def _write_csv(path, rows):
    header = "date,ticker,action,qty,price\n"
    body = "\n".join(f"{d},{t},{a},{q},{p}" for d, t, a, q, p in rows)
    path.write_text(header + body + "\n", encoding="utf-8")


def test_load_transactions_sem_arquivo_retorna_vazio(tmp_path):
    assert load_transactions(tmp_path / "nao-existe.csv") == []


def test_load_transactions_ordena_por_data(tmp_path):
    path = tmp_path / "transactions.csv"
    _write_csv(
        path,
        [
            ("2026-03-15", "VWRA11", "compra", 10, 112.40),
            ("2026-01-10", "B5P211", "compra", 65, 105.20),
        ],
    )
    transactions = load_transactions(path)
    assert [t.ticker for t in transactions] == ["B5P211", "VWRA11"]


def test_current_holdings_soma_compra_e_subtrai_venda(tmp_path):
    path = tmp_path / "transactions.csv"
    _write_csv(
        path,
        [
            ("2026-01-10", "B5P211", "compra", 65, 105.20),
            ("2026-02-01", "B5P211", "compra", 10, 108.00),
            ("2026-03-01", "B5P211", "venda", 5, 110.00),
        ],
    )
    transactions = load_transactions(path)
    assert current_holdings(transactions) == {"B5P211": 70}


def test_holdings_at_respeita_a_data_de_corte(tmp_path):
    path = tmp_path / "transactions.csv"
    _write_csv(
        path,
        [
            ("2026-01-10", "B5P211", "compra", 65, 105.20),
            ("2026-06-01", "B5P211", "compra", 20, 120.00),
        ],
    )
    transactions = load_transactions(path)
    assert holdings_at(transactions, date(2026, 3, 1)) == {"B5P211": 65.0}
    assert holdings_at(transactions, date(2026, 6, 1)) == {"B5P211": 85.0}


def test_total_invested_at_acumula_compras_e_subtrai_vendas(tmp_path):
    path = tmp_path / "transactions.csv"
    _write_csv(
        path,
        [
            ("2026-01-10", "B5P211", "compra", 65, 100.00),  # 6500
            ("2026-02-01", "VWRA11", "compra", 10, 110.00),  # 1100
            ("2026-03-01", "B5P211", "venda", 5, 105.00),  # -525
        ],
    )
    transactions = load_transactions(path)
    assert total_invested_at(transactions, date(2026, 1, 15)) == 6500.0
    assert total_invested_at(transactions, date(2026, 2, 15)) == 7600.0
    assert total_invested_at(transactions, date(2026, 3, 15)) == 7075.0


def test_first_transaction_date(tmp_path):
    path = tmp_path / "transactions.csv"
    _write_csv(path, [("2026-01-10", "B5P211", "compra", 65, 100.00)])
    transactions = load_transactions(path)
    assert first_transaction_date(transactions) == date(2026, 1, 10)


def test_first_transaction_date_vazio_retorna_none():
    assert first_transaction_date([]) is None


def test_transaction_signed_qty_e_signed_value():
    compra = Transaction(date(2026, 1, 1), "B5P211", "compra", 10, 100.0)
    venda = Transaction(date(2026, 1, 1), "B5P211", "venda", 4, 110.0)
    assert compra.signed_qty == 10
    assert compra.signed_value == 1000.0
    assert venda.signed_qty == -4
    assert venda.signed_value == -440.0
