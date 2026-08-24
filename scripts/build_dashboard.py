"""Gera docs/index.html — o dashboard de performance publicado no GitHub
Pages. Roda 1x/dia junto com o monitor de bandas.

Qualquer falha aqui não deve derrubar o monitor de bandas: o workflow roda
este script como um step separado, e uma falha de dashboard não impede o
alerta de banda de funcionar.
"""
from __future__ import annotations

import os
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from monitor.allocation import compute_statuses  # noqa: E402
from monitor.config import load_portfolio  # noqa: E402
from monitor.dashboard import build_dashboard_html  # noqa: E402
from monitor.historical_prices import HistoricalPriceFetchError, fetch_historical_prices  # noqa: E402
from monitor.ipca import IpcaFetchError, fetch_ipca_monthly  # noqa: E402
from monitor.performance import compute_performance, compute_wealth_series  # noqa: E402
from monitor.prices import PriceFetchError, fetch_prices  # noqa: E402
from monitor.transactions import first_transaction_date, load_transactions  # noqa: E402

DOCS_PATH = REPO_ROOT / "docs" / "index.html"


def main() -> int:
    brapi_token = os.environ.get("BRAPI_TOKEN")
    if not brapi_token:
        print("Erro: BRAPI_TOKEN não configurado.", file=sys.stderr)
        return 1

    targets = load_portfolio()
    transactions = load_transactions()
    if not transactions:
        print("Sem transações em config/transactions.csv — nada a mostrar ainda.", file=sys.stderr)
        return 1

    inicio = first_transaction_date(transactions)
    hoje = datetime.now(timezone.utc).date()

    try:
        current_prices = fetch_prices(list(targets.keys()), brapi_token)
    except PriceFetchError as exc:
        print(f"Erro ao buscar cotações atuais: {exc}", file=sys.stderr)
        return 1

    holdings = {}
    for t in transactions:
        holdings[t.ticker] = holdings.get(t.ticker, 0) + t.signed_qty
    holdings = {k: int(round(v)) for k, v in holdings.items()}
    statuses = compute_statuses(holdings, current_prices, targets)

    price_history: dict[str, list[tuple[date, float]]] = {}
    all_dates: set[date] = set()
    for ticker in targets:
        try:
            historico = fetch_historical_prices(ticker, brapi_token)
        except HistoricalPriceFetchError as exc:
            print(f"Aviso: sem histórico de preço para {ticker}: {exc}", file=sys.stderr)
            continue
        price_history[ticker] = historico
        all_dates.update(d for d, _ in historico if d >= inicio)
    all_dates.add(hoje)

    try:
        ipca_monthly = fetch_ipca_monthly(inicio - timedelta(days=31), hoje)
    except IpcaFetchError as exc:
        print(f"Aviso: sem dado de IPCA, performance real ficará vazia: {exc}", file=sys.stderr)
        ipca_monthly = []

    wealth_series = compute_wealth_series(transactions, price_history, sorted(all_dates))
    performance_points = compute_performance(transactions, wealth_series, ipca_monthly)

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    html = build_dashboard_html(statuses, performance_points, generated_at)

    DOCS_PATH.parent.mkdir(exist_ok=True)
    DOCS_PATH.write_text(html, encoding="utf-8")
    print(f"Dashboard gerado em {DOCS_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
