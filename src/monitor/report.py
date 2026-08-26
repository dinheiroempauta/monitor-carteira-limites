"""Monta o texto do relatório em pt-BR a partir dos cálculos de alocação.

Duas versões: uma completa (com R$, pro log da execução) e uma pro
Telegram, que mostra só percentuais nas posições — de propósito, pra não
virar um lugar de ficar acompanhando o tamanho da carteira em R$. Valores
em R$ no Telegram aparecem só onde são acionáveis (quanto aportar, quanto
vender), nunca no tamanho da posição em si.
"""
from __future__ import annotations

from monitor.allocation import STATUS_ABAIXO, STATUS_ACIMA, AportePlan, AssetStatus, RebalanceAction

STATUS_LABEL = {
    STATUS_ABAIXO: "🔵 abaixo da banda",
    STATUS_ACIMA: "🔴 acima da banda",
    "ok": "✅ dentro da banda",
}

# Mesmo texto de STATUS_LABEL, mas capitalizado — usado como linha própria
# (não no meio de frase) no bloco de posição do monitor periódico.
STATUS_LABEL_LINHA = {
    STATUS_ABAIXO: "🔵 Abaixo da banda",
    STATUS_ACIMA: "🔴 Acima da banda",
    "ok": "✅ Dentro da banda",
}

IR_NOTE = (
    "Lembrete: venda pode gerar IR (isenções e alíquotas variam por tipo de "
    "ativo — confira antes de vender)."
)


def _cotas(qty: int) -> str:
    return "1 cota" if qty == 1 else f"{qty} cotas"


def _brl(valor: float) -> str:
    """Formata em pt-BR (milhar com ponto, decimal com vírgula): 4.587,90."""
    return f"{valor:,.2f}".translate(str.maketrans(",.", ".,"))


def _position_lines(statuses: list[AssetStatus], show_values: bool) -> list[str]:
    lines = []
    for s in statuses:
        lines.append(f"◾ *{s.ticker}* = {s.pct:.1%}")
        lines.append(f"◾ Alvo = {s.target.target:.0%}")
        lines.append(f"◾ Banda = {s.target.min:.0%}-{s.target.max:.0%}")
        if show_values:
            lines.append(f"◾ Valor = R$ {_brl(s.value)} ({_cotas(s.qty)} × R$ {_brl(s.price)})")
        lines.append(STATUS_LABEL_LINHA[s.status])
        lines.append("")
    return lines


def _actions_section(actions: list[RebalanceAction]) -> list[str]:
    """O monitor periódico só sugere venda (nunca compra — isso é decidido
    à parte, via aporte). Sem ativo acima do teto, não há nada a fazer
    aqui: o status de cada ativo já apareceu no bloco de posição acima."""
    if not actions:
        return ["✅ Nenhuma venda necessária."]

    lines = ["⚠️ *Venda recomendada* (excedente em relação ao teto da banda):", ""]
    for a in actions:
        lines.append(f"◾ Vender {_cotas(a.qty)} de *{a.ticker}* (aprox. R$ {_brl(a.approx_value)})")
    lines.append("")
    lines.append(IR_NOTE)
    return lines


def build_report(
    statuses: list[AssetStatus],
    actions: list[RebalanceAction],
    quotas_metadata: dict,
    *,
    show_values: bool = True,
) -> str:
    lines = ["📊 *Monitor de Carteira*", ""]
    lines.extend(_position_lines(statuses, show_values))

    if show_values:
        total = sum(s.value for s in statuses)
        lines.append(f"Valor total: R$ {_brl(total)}")
    lines.append(f"Posição atualizada em: {quotas_metadata.get('updated_at')} (fonte: {quotas_metadata.get('source')})")
    lines.append("")

    lines.extend(_actions_section(actions))

    return "\n".join(lines)


def build_aporte_report(plan: AportePlan, statuses_atuais: list[AssetStatus], aporte: float) -> str:
    """Mensagem de Telegram (texto simples, sem markdown de tabela — o app
    do Telegram não renderiza tabela) com o plano de compra sob demanda de
    aporte_quotas_plan. Pensada pra ser disparada por um workflow_dispatch
    com o campo `aporte` preenchido, sem precisar de nenhum agente no
    caminho — ver .claude/skills/aporte-rebalanceamento/SKILL.md."""
    price = {s.ticker: s.price for s in statuses_atuais}
    lines = [f"💰 *Aporte de R$ {_brl(aporte)}*", ""]

    gasto_total = sum(qty * price[t] for t, qty in plan.purchases.items())
    for s in sorted(plan.final_statuses, key=lambda s: -s.value):
        qty_comprada = plan.purchases.get(s.ticker, 0)
        if qty_comprada:
            custo = qty_comprada * price[s.ticker]
            linha_compra = f"{_cotas(qty_comprada)} (R$ {_brl(custo)})"
        else:
            linha_compra = "0 cotas"
        lines.append(f"◾ *{s.ticker}* — {linha_compra}")
        lines.append(
            f"→ fica em {s.pct:.1%} (alvo {s.target.target:.0%}, "
            f"banda {s.target.min:.0%}-{s.target.max:.0%}) {STATUS_LABEL[s.status]}"
        )
        lines.append("")

    lines.append(f"*Total investido:* R$ {_brl(gasto_total)}")
    if plan.leftover > 0.01:
        lines.append(f"Troco não investido: R$ {_brl(plan.leftover)} (nenhuma cota cabia sem sair do alvo de alguém).")

    if any(s.status != "ok" for s in plan.final_statuses):
        lines.append("")
        lines.append(
            "⚠️ Esse aporte não foi suficiente para trazer todo mundo pra dentro da banda — "
            "os ativos acima ainda fora dela continuam precisando de atenção."
        )

    return "\n".join(lines)
