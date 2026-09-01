import importlib.util
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

_spec = importlib.util.spec_from_file_location("backfill_wealth_history", REPO_ROOT / "scripts" / "backfill_wealth_history.py")
backfill_wealth_history = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(backfill_wealth_history)

from monitor.transactions import Transaction  # noqa: E402

COMPRA = "compra"


def test_backfill_range_none_sem_transacoes():
    assert backfill_wealth_history.backfill_range([], [], date(2026, 8, 30)) is None


def test_backfill_range_none_quando_ja_cobre_desde_a_primeira_transacao():
    transactions = [Transaction(date(2026, 8, 4), "B5P211", COMPRA, 10, 109.55)]
    existentes = [{"date": "2026-08-04"}]
    assert backfill_wealth_history.backfill_range(transactions, existentes, date(2026, 8, 30)) is None


def test_backfill_range_cobre_ate_o_dia_anterior_ao_primeiro_ponto_existente():
    transactions = [Transaction(date(2026, 8, 4), "B5P211", COMPRA, 10, 109.55)]
    existentes = [{"date": "2026-08-24"}]
    assert backfill_wealth_history.backfill_range(transactions, existentes, date(2026, 8, 30)) == (
        date(2026, 8, 4),
        date(2026, 8, 23),
    )


def test_backfill_range_ate_hoje_quando_wealth_history_esta_vazio():
    transactions = [Transaction(date(2026, 8, 4), "B5P211", COMPRA, 10, 109.55)]
    assert backfill_wealth_history.backfill_range(transactions, [], date(2026, 8, 6)) == (
        date(2026, 8, 4),
        date(2026, 8, 6),
    )


def test_build_backfill_rows_usa_carry_forward_em_dia_sem_pregao():
    transactions = [Transaction(date(2026, 8, 4), "B5P211", COMPRA, 10, 109.55)]
    historico = {"B5P211": {"2026-08-04": 109.55}}  # sem preço pro dia 5 (fim de semana, p.ex.)

    rows = backfill_wealth_history.build_backfill_rows(transactions, historico, date(2026, 8, 4), date(2026, 8, 5))

    assert [r["date"] for r in rows] == ["2026-08-04", "2026-08-05"]
    assert rows[0]["wealth"] == "1095.50"
    assert rows[1]["wealth"] == "1095.50"  # carrega o preço do dia 4
    assert rows[0]["invested"] == "1095.50"
    assert rows[0]["nominal_return"] == "0.000000"


def test_build_backfill_rows_pula_dias_antes_da_primeira_compra_do_ticker():
    transactions = [
        Transaction(date(2026, 8, 4), "B5P211", COMPRA, 10, 109.55),
        Transaction(date(2026, 8, 6), "VWRA11", COMPRA, 5, 113.99),
    ]
    historico = {"B5P211": {"2026-08-04": 109.55}, "VWRA11": {"2026-08-06": 113.99}}

    rows = backfill_wealth_history.build_backfill_rows(transactions, historico, date(2026, 8, 4), date(2026, 8, 6))

    assert [r["date"] for r in rows] == ["2026-08-04", "2026-08-05", "2026-08-06"]
    assert rows[2]["wealth"] == f"{10 * 109.55 + 5 * 113.99:.2f}"


def test_build_backfill_rows_pula_dias_sem_nenhuma_cotacao_conhecida_ainda():
    transactions = [Transaction(date(2026, 8, 4), "B5P211", COMPRA, 10, 109.55)]
    historico = {"B5P211": {}}  # brapi não devolveu histórico suficiente pra cobrir o dia 4

    rows = backfill_wealth_history.build_backfill_rows(transactions, historico, date(2026, 8, 4), date(2026, 8, 4))

    assert rows == []
