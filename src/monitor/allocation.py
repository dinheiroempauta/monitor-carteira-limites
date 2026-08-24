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


def effective_status_for_alerting(
    statuses: list[AssetStatus], last_status: dict[str, str], hysteresis: float = 0.01
) -> dict[str, str]:
    """Status por ticker a usar na comparação "mudou desde o último alerta?".

    Igual ao status real, exceto que a transição de volta para "ok" só é
    reconhecida quando o ativo recupera com uma margem (`hysteresis`, em
    pontos percentuais) além da borda da banda — evita que um ativo
    oscilando bem em cima do limite dispare vários alertas seguidos.
    Entrar numa banda (ok -> fora) sempre é reconhecido na hora, sem
    atraso: esse sinal deve ser imediato.
    """
    effective = {}
    for s in statuses:
        prev = last_status.get(s.ticker)
        if prev == STATUS_ABAIXO and s.status == STATUS_OK and s.pct < s.target.min + hysteresis:
            effective[s.ticker] = prev
        elif prev == STATUS_ACIMA and s.status == STATUS_OK and s.pct > s.target.max - hysteresis:
            effective[s.ticker] = prev
        else:
            effective[s.ticker] = s.status
    return effective


def resolve_via_aporte(
    statuses: list[AssetStatus], max_aporte_multiplier: float = 2.0
) -> dict[str, float] | None:
    """Se houver ativo fora da banda, calcula o menor aporte (distribuído
    conforme `contribution_suggestion`) que traz todos de volta para dentro
    da banda — sem precisar vender nada. Um aporte novo dilui os ativos que
    não o recebem (reduz o % deles) e reforça diretamente os que recebem.

    Retorna {ticker: valor_a_aportar} (só os tickers com valor > 0) ou
    None se não há fora de banda, ou se o aporte necessário passaria de
    `max_aporte_multiplier` vezes o valor total da carteira (impraticável
    — nesse caso vender é a via realista).
    """
    if all(s.status == STATUS_OK for s in statuses):
        return None

    total = sum(s.value for s in statuses)
    weights = contribution_suggestion(statuses)
    if not any(w > 0 for w in weights.values()):
        return None  # não há para onde direcionar aporte (não deveria acontecer)

    def dentro_da_banda(aporte: float) -> bool:
        novo_total = total + aporte
        for s in statuses:
            novo_valor = s.value + aporte * weights.get(s.ticker, 0.0)
            novo_pct = novo_valor / novo_total
            if not (s.target.min - 1e-9 <= novo_pct <= s.target.max + 1e-9):
                return False
        return True

    # A região de aporte que resolve tudo não é necessariamente "qualquer
    # valor grande" — um aporte enorme dilui até os ativos que já estavam
    # ok para baixo do próprio piso deles. Ou seja, "dentro da banda" pode
    # ser falso perto de 0 (breach atual), virar verdadeiro numa faixa
    # intermediária, e voltar a ser falso para aportes exagerados. Por
    # isso varremos em vez de assumir monotonicidade global.
    cap = total * max_aporte_multiplier
    steps = 500
    prev_c, prev_ok = 0.0, dentro_da_banda(0.0)
    lo = hi = None
    for i in range(1, steps + 1):
        c = cap * i / steps
        ok = dentro_da_banda(c)
        if ok and not prev_ok:
            lo, hi = prev_c, c
            break
        prev_c, prev_ok = c, ok

    if lo is None:
        return None  # nenhum aporte até o teto resolve sozinho — vender é necessário

    for _ in range(60):
        mid = (lo + hi) / 2
        if dentro_da_banda(mid):
            hi = mid
        else:
            lo = mid

    return {ticker: hi * weight for ticker, weight in weights.items() if weight > 0}
