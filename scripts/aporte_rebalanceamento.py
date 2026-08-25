"""Dado um valor de aporte e os preços atuais dos ativos, calcula quantas
cotas comprar de cada um para tirar todo mundo da banda primeiro e só
depois aproximar do alvo (ver monitor.allocation.aporte_quotas_plan) —
e imprime duas tabelas em markdown (situação atual / depois do aporte).

Os preços não são buscados por este script: rodam num ambiente sem acesso
à brapi.dev. Precisam vir de uma execução real do workflow (ver skill
"aporte-rebalanceamento" em .claude/skills/), pelo log do step "Rodar
monitor e notificar".

Uso:
    python scripts/aporte_rebalanceamento.py --aporte 4587.90 \
        --preco B5P211=110.62 --preco VWRA11=114.62 --preco DIVO11=123.71 \
        --preco CDIB11=51.57 --preco GOLD11=24.88
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from monitor.allocation import aporte_quotas_plan, compute_statuses  # noqa: E402
from monitor.config import load_portfolio, load_quotas  # noqa: E402
from monitor.report import STATUS_LABEL  # noqa: E402


def brl(valor: float) -> str:
    """Formata em pt-BR (milhar com ponto, decimal com vírgula): R$ 4.587,90."""
    return f"{valor:,.2f}".translate(str.maketrans(",.", ".,"))


def parse_precos(pares: list[str]) -> dict[str, float]:
    precos = {}
    for par in pares:
        ticker, _, valor = par.partition("=")
        if not ticker or not valor:
            raise SystemExit(f"--preco inválido: {par!r} (esperado TICKER=VALOR)")
        precos[ticker.strip().upper()] = float(valor.replace(",", "."))
    return precos


def formatar_tabela_atual(statuses) -> str:
    linhas = [
        "| Ativo | Cotas | Preço | Valor | % atual | Alvo | Banda | Status |",
        "|---|---|---|---|---|---|---|---|",
    ]
    total = sum(s.value for s in statuses)
    for s in sorted(statuses, key=lambda s: -s.value):
        linhas.append(
            f"| {s.ticker} | {s.qty} | R$ {brl(s.price)} | R$ {brl(s.value)} | {s.pct:.1%} | "
            f"{s.target.target:.0%} | {s.target.min:.0%}–{s.target.max:.0%} | {STATUS_LABEL[s.status]} |"
        )
    linhas.append(f"| **Total** | | | **R$ {brl(total)}** | | | | |")
    return "\n".join(linhas)


def formatar_tabela_pos_aporte(plan, statuses_atuais, aporte: float) -> str:
    linhas = [
        "| Ativo | Compra | Cotas | Valor novo | % nova | Alvo | Banda | Status |",
        "|---|---|---|---|---|---|---|---|",
    ]
    total = sum(s.value for s in plan.final_statuses)
    for s in sorted(plan.final_statuses, key=lambda s: -s.value):
        qty_comprada = plan.purchases.get(s.ticker, 0)
        custo = qty_comprada * s.price
        linhas.append(
            f"| {s.ticker} | +{qty_comprada} (R$ {brl(custo)}) | {s.qty} | R$ {brl(s.value)} | {s.pct:.1%} | "
            f"{s.target.target:.0%} | {s.target.min:.0%}–{s.target.max:.0%} | {STATUS_LABEL[s.status]} |"
        )
    gasto_total = sum(plan.purchases.get(t, 0) * s.price for t, s in ((s.ticker, s) for s in statuses_atuais))
    linhas.append(f"| **Total** | **R$ {brl(gasto_total)}** | | **R$ {brl(total)}** | | | | |")
    if plan.leftover > 0.01:
        linhas.append("")
        linhas.append(f"Troco não investido: R$ {brl(plan.leftover)} (nenhuma cota cabia sem sair do alvo de alguém).")
    return "\n".join(linhas)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--aporte", type=float, required=True, help="Valor do aporte em R$")
    parser.add_argument(
        "--preco",
        action="append",
        required=True,
        metavar="TICKER=VALOR",
        help="Preço atual de um ativo (repita uma vez por ticker do portfolio.yaml)",
    )
    args = parser.parse_args()

    targets = load_portfolio()
    holdings = load_quotas()
    precos = parse_precos(args.preco)

    faltando = set(targets) - set(precos)
    if faltando:
        raise SystemExit(f"Faltam preços para: {', '.join(sorted(faltando))}")

    statuses = compute_statuses(holdings, precos, targets)
    plan = aporte_quotas_plan(statuses, args.aporte)

    print("## Situação atual\n")
    print(formatar_tabela_atual(statuses))
    print(f"\n## Depois do aporte de R$ {brl(args.aporte)}\n")
    print(formatar_tabela_pos_aporte(plan, statuses, args.aporte))
    return 0


if __name__ == "__main__":
    sys.exit(main())
