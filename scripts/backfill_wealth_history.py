"""Reconstrói config/wealth_history.csv desde a primeira transação em
config/transactions.csv, usando preço histórico de fechamento (brapi.dev).

Rodar uma vez (ou sempre que houver uma lacuna entre a primeira transação e
o primeiro ponto já registrado em wealth_history.csv) para que o gráfico de
patrimônio comece no dia zero da carteira em vez do dia em que o dashboard
passou a rodar. Dias sem pregão (fim de semana/feriado) usam o último preço
de fechamento disponível (carry-forward), igual à posição real da carteira
nesses dias.

Não sobrescreve pontos já existentes em wealth_history.csv — só preenche o
que falta antes do primeiro ponto atual (ou, se o arquivo estiver vazio,
gera a série inteira até hoje).
"""
from __future__ import annotations

import os
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from monitor.config import append_wealth_history, load_wealth_history  # noqa: E402
from monitor.prices import PriceFetchError, fetch_historical_prices  # noqa: E402
from monitor.transactions import Transaction, first_transaction_date, holdings_at, load_transactions, total_invested_at  # noqa: E402


def _daterange(start: date, end: date):
    day = start
    while day <= end:
        yield day
        day += timedelta(days=1)


def _range_covering(start: date, end: date) -> str:
    dias = (end - start).days
    for limite, nome in ((30, "1mo"), (90, "3mo"), (180, "6mo"), (365, "1y"), (730, "2y"), (1825, "5y")):
        if dias <= limite:
            return nome
    return "max"


def backfill_range(
    transactions: list[Transaction], existentes: list[dict], hoje: date
) -> tuple[date, date] | None:
    """Determina o intervalo [inicio, fim] a preencher, ou None se não há
    lacuna (sem transações, ou wealth_history.csv já cobre desde a
    primeira transação)."""
    inicio = first_transaction_date(transactions)
    if inicio is None:
        return None

    primeiro_existente = min((date.fromisoformat(r["date"]) for r in existentes), default=hoje + timedelta(days=1))
    fim = min(primeiro_existente - timedelta(days=1), hoje)
    if inicio > fim:
        return None
    return inicio, fim


def build_backfill_rows(
    transactions: list[Transaction], historico: dict[str, dict[str, float]], inicio: date, fim: date
) -> list[dict]:
    """Reconstrói, dia a dia, as linhas de wealth_history entre `inicio` e
    `fim` (inclusive) a partir da posição em cada dia (`holdings_at`) e do
    preço de fechamento mais recente conhecido até aquele dia
    (carry-forward pra fins de semana/feriados sem pregão)."""
    tickers = sorted({t.ticker for t in transactions})
    ultimo_preco: dict[str, float] = {}
    rows = []
    for dia in _daterange(inicio, fim):
        chave = dia.isoformat()
        for ticker in tickers:
            preco_do_dia = historico.get(ticker, {}).get(chave)
            if preco_do_dia is not None:
                ultimo_preco[ticker] = preco_do_dia

        posicao = holdings_at(transactions, dia)
        if not any(qty for qty in posicao.values()):
            continue  # antes de qualquer compra, nada a somar

        wealth = sum(qty * ultimo_preco[ticker] for ticker, qty in posicao.items() if qty and ticker in ultimo_preco)
        if wealth == 0:
            continue  # ainda sem cotação conhecida pra nenhum ativo em carteira nesse dia

        invested = total_invested_at(transactions, dia)
        nominal = (wealth - invested) / invested if invested else 0.0

        rows.append(
            {
                "date": chave,
                "wealth": f"{wealth:.2f}",
                "invested": f"{invested:.2f}",
                "nominal_return": f"{nominal:.6f}",
                "real_return": "",
            }
        )
    return rows


def main() -> int:
    brapi_token = os.environ.get("BRAPI_TOKEN")
    if not brapi_token:
        print("Erro: BRAPI_TOKEN não configurado.", file=sys.stderr)
        return 1

    transactions = load_transactions()
    hoje = datetime.now(timezone.utc).date()
    existentes = load_wealth_history()

    intervalo = backfill_range(transactions, existentes, hoje)
    if intervalo is None:
        print("Sem transações, ou wealth_history.csv já cobre desde a primeira transação — nada a fazer.")
        return 0
    inicio, fim = intervalo

    tickers = sorted({t.ticker for t in transactions})
    range_ = _range_covering(inicio, hoje)
    try:
        historico = fetch_historical_prices(tickers, brapi_token, range_)
    except PriceFetchError as exc:
        print(f"Erro ao buscar histórico de preços: {exc}", file=sys.stderr)
        return 1

    rows = build_backfill_rows(transactions, historico, inicio, fim)
    for row in rows:
        append_wealth_history(row)

    print(f"{len(rows)} ponto(s) adicionado(s) a config/wealth_history.csv (de {inicio} até {fim}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
