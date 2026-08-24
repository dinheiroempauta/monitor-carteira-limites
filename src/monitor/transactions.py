"""Registro de transações (compras/vendas) — fonte de verdade da posição
atual e da base para os cálculos de performance. Substitui a edição manual
de quotas.yaml: a posição de cada ticker é a soma das transações.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TRANSACTIONS_PATH = REPO_ROOT / "config" / "transactions.csv"

COMPRA = "compra"
VENDA = "venda"


@dataclass(frozen=True)
class Transaction:
    date: date
    ticker: str
    action: str  # "compra" | "venda"
    qty: float
    price: float

    @property
    def signed_qty(self) -> float:
        return self.qty if self.action == COMPRA else -self.qty

    @property
    def signed_value(self) -> float:
        return self.qty * self.price if self.action == COMPRA else -self.qty * self.price


def load_transactions(path: Path = TRANSACTIONS_PATH) -> list[Transaction]:
    if not path.exists():
        return []
    transactions = []
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            action = row["action"].strip().lower()
            if action not in (COMPRA, VENDA):
                raise ValueError(f"Ação inválida em transactions.csv: {row['action']!r} (use 'compra' ou 'venda')")
            transactions.append(
                Transaction(
                    date=datetime.strptime(row["date"].strip(), "%Y-%m-%d").date(),
                    ticker=row["ticker"].strip(),
                    action=action,
                    qty=float(row["qty"]),
                    price=float(row["price"]),
                )
            )
    return sorted(transactions, key=lambda t: t.date)


def current_holdings(transactions: list[Transaction]) -> dict[str, int]:
    """Posição atual por ticker (soma de compras menos vendas)."""
    holdings: dict[str, float] = {}
    for t in transactions:
        holdings[t.ticker] = holdings.get(t.ticker, 0.0) + t.signed_qty
    return {ticker: int(round(qty)) for ticker, qty in holdings.items()}


def holdings_at(transactions: list[Transaction], as_of: date) -> dict[str, float]:
    """Posição por ticker na data `as_of` (inclusive), usada para reconstruir
    o patrimônio ao longo do tempo."""
    holdings: dict[str, float] = {}
    for t in transactions:
        if t.date <= as_of:
            holdings[t.ticker] = holdings.get(t.ticker, 0.0) + t.signed_qty
    return holdings


def total_invested_at(transactions: list[Transaction], as_of: date) -> float:
    """Total investido acumulado até `as_of` (compras somam, vendas
    subtraem — ver limitação sobre apuração de venda em plan.md)."""
    return sum(t.signed_value for t in transactions if t.date <= as_of)


def first_transaction_date(transactions: list[Transaction]) -> date | None:
    return transactions[0].date if transactions else None
