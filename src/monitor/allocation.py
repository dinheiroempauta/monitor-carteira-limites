"""Lógica de alocação: status por banda, plano de venda/compra e sugestão
de aporte. Não depende de I/O — só de números — para ser fácil de testar."""
from __future__ import annotations

import math
from dataclasses import dataclass

from monitor.config import AssetTarget

STATUS_OK = "ok"
STATUS_ABAIXO = "abaixo_da_banda"
STATUS_ACIMA = "acima_da_banda"


@dataclass(frozen=True)
class AssetStatus:
    ticker: str
    qty: int
    price: float
    value: float
    pct: float
    target: AssetTarget
    status: str


@dataclass(frozen=True)
class RebalanceAction:
    ticker: str
    action: str  # "vender" | "comprar"
    qty: int
    approx_value: float


def compute_statuses(
    holdings: dict[str, int], prices: dict[str, float], targets: dict[str, AssetTarget]
) -> list[AssetStatus]:
    values = {t: holdings[t] * prices[t] for t in targets}
    total = sum(values.values())
    if total <= 0:
        raise ValueError("Valor total da carteira é zero — confira as quantidades em quotas.yaml")

    statuses = []
    for ticker, target in targets.items():
        value = values[ticker]
        pct = value / total
        if pct < target.min:
            status = STATUS_ABAIXO
        elif pct > target.max:
            status = STATUS_ACIMA
        else:
            status = STATUS_OK
        statuses.append(
            AssetStatus(
                ticker=ticker,
                qty=holdings[ticker],
                price=prices[ticker],
                value=value,
                pct=pct,
                target=target,
                status=status,
            )
        )
    return statuses


def rebalance_plan(statuses: list[AssetStatus]) -> list[RebalanceAction]:
    """Retorna ações de venda/compra para trazer os ativos fora da banda de
    volta ao alvo. Lista vazia = nenhuma ação necessária (todos dentro da
    banda)."""
    total = sum(s.value for s in statuses)
    actions = []
    for s in statuses:
        if s.status == STATUS_OK:
            continue
        target_value = s.target.target * total
        diff_value = s.value - target_value  # positivo = tem excesso, vender
        qty = math.floor(abs(diff_value) / s.price)
        if qty <= 0:
            continue
        if diff_value > 0:
            actions.append(RebalanceAction(s.ticker, "vender", qty, qty * s.price))
        else:
            actions.append(RebalanceAction(s.ticker, "comprar", qty, qty * s.price))
    return actions


def contribution_suggestion(statuses: list[AssetStatus]) -> dict[str, float]:
    """Sugestão de para onde direcionar o próximo aporte, como peso (0-1)
    por ticker, somando 1. Prioriza os ativos mais abaixo do alvo; se
    nenhum estiver abaixo do alvo, sugere pesos iguais ao alvo."""
    gaps = {s.ticker: max(0.0, s.target.target - s.pct) for s in statuses}
    total_gap = sum(gaps.values())
    if total_gap <= 0:
        return {s.ticker: s.target.target for s in statuses}
    return {ticker: gap / total_gap for ticker, gap in gaps.items()}
