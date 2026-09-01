"""Gera docs/index.html — o dashboard de performance publicado no GitHub
Pages. Roda 1x/dia junto com o monitor de bandas.

Acumula um ponto por dia em config/wealth_history.csv a partir de hoje. O
histórico anterior a isso (desde a primeira transação) é preenchido uma
vez por scripts/backfill_wealth_history.py, usando preço de fechamento
histórico da brapi.dev — rodar esse script sempre que houver uma lacuna
(ex.: numa carteira nova, antes do primeiro `wealth_history.csv` existir).

Qualquer falha aqui não deve derrubar o monitor de bandas: o workflow roda
este script como um step separado, e uma falha de dashboard não impede o
alerta de banda de funcionar.
"""
from __future__ import annotations

import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from monitor.allocation import compute_statuses  # noqa: E402
from monitor.config import append_wealth_history, load_portfolio, load_wealth_history  # noqa: E402
from monitor.dashboard import build_dashboard_html  # noqa: E402
from monitor.ipca import IpcaFetchError, fetch_ipca_monthly  # noqa: E402
from monitor.performance import compute_monthly_returns, compute_nominal_return, compute_real_return  # noqa: E402
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
    inicio_mes = date(inicio.year, inicio.month, 1)

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
        # Busca a partir do 1º dia do MÊS da primeira transação (não 31
        # dias antes) — evita puxar sem querer o IPCA de um mês anterior
        # ao início do acompanhamento, que não deveria entrar em nenhuma
        # conta de retorno real daqui.
        ipca_monthly = fetch_ipca_monthly(inicio_mes, hoje)
    except IpcaFetchError as exc:
        print(f"Aviso: sem dado de IPCA, performance real ficará vazia: {exc}", file=sys.stderr)
        ipca_monthly = []

    # Índice acumulado (KPI do topo, "desde o início"): só meses a partir
    # do mês da primeira transação — sempre true por construção do fetch
    # acima, mas o filtro fica explícito aqui para não depender só do
    # range da busca.
    ipca_desde_inicio = [(d, v) for d, v in ipca_monthly if (d.year, d.month) >= (inicio_mes.year, inicio_mes.month)]
    real = compute_real_return(nominal, ipca_desde_inicio)

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

    ipca_by_month = {(d.year, d.month): v for d, v in ipca_monthly}
    daily_points = [
        (date.fromisoformat(r["date"]), float(r["wealth"]), float(r["invested"])) for r in wealth_history
    ]
    monthly_returns = compute_monthly_returns(daily_points, ipca_by_month)

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    html = build_dashboard_html(statuses, wealth_history, monthly_returns, generated_at)

    DOCS_PATH.parent.mkdir(exist_ok=True)
    DOCS_PATH.write_text(html, encoding="utf-8")
    print(f"Dashboard gerado em {DOCS_PATH} (patrimônio: R$ {wealth:,.2f}, nominal: {nominal:.2%})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
