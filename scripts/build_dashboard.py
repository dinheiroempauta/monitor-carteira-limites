"""Gera docs/index.html — o dashboard de performance publicado no GitHub
Pages. Roda 1x/dia junto com o monitor de bandas.

Não reconstrói o passado (sem histórico de preço): acumula um ponto por
dia em config/wealth_history.csv a partir de quando começou a rodar.

Qualquer falha aqui não deve derrubar o monitor de bandas: o workflow roda
este script como um step separado, e uma falha de dashboard não impede o
alerta de banda de funcionar.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from monitor.allocation import compute_statuses  # noqa: E402
from monitor.config import append_wealth_history, load_portfolio, load_wealth_history  # noqa: E402
from monitor.dashboard import build_dashboard_html  # noqa: E402
from monitor.ipca import IpcaFetchError, fetch_ipca_monthly  # noqa: E402
from monitor.performance import compute_nominal_return, compute_real_return  # noqa: E402
from monitor.prices import PriceFetchError, fetch_prices  # noqa: E402
from monitor.transactions import current_holdings, first_transaction_date, load_transactions, total_invested_at  # noqa: E402

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

    hoje = datetime.now(timezone.utc).date()
    inicio = first_transaction_date(transactions)

    try:
        current_prices = fetch_prices(list(targets.keys()), brapi_token)
    except PriceFetchError as exc:
        print(f"Erro ao buscar cotações atuais: {exc}", file=sys.stderr)
        return 1

    holdings = current_holdings(transactions)
    statuses = compute_statuses(holdings, current_prices, targets)

    wealth = sum(s.value for s in statuses)
    invested = total_invested_at(transactions, hoje)
    nominal = compute_nominal_return(wealth, invested)

    try:
        ipca_monthly = fetch_ipca_monthly(inicio - timedelta(days=31), hoje)
    except IpcaFetchError as exc:
        print(f"Aviso: sem dado de IPCA, performance real ficará vazia: {exc}", file=sys.stderr)
        ipca_monthly = []
    real = compute_real_return(nominal, ipca_monthly)

    append_wealth_history(
        {
            "date": hoje.isoformat(),
            "wealth": f"{wealth:.2f}",
            "invested": f"{invested:.2f}",
            "nominal_return": f"{nominal:.6f}",
            "real_return": f"{real:.6f}" if real is not None else "",
        }
    )

    wealth_history = load_wealth_history()
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    html = build_dashboard_html(statuses, wealth_history, generated_at)

    DOCS_PATH.parent.mkdir(exist_ok=True)
    DOCS_PATH.write_text(html, encoding="utf-8")
    print(f"Dashboard gerado em {DOCS_PATH} (patrimônio: R$ {wealth:,.2f}, nominal: {nominal:.2%})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
