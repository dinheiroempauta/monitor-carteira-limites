"""Monta o texto do relatório em pt-BR a partir dos cálculos de alocação.

Duas versões: uma completa (com R$, pro log da execução) e uma pro
Telegram, que mostra só percentuais nas posições — de propósito, pra não
virar um lugar de ficar acompanhando o tamanho da carteira em R$. Valores
em R$ no Telegram aparecem só onde são acionáveis (quanto aportar, quanto
vender), nunca no tamanho da posição em si.
"""
from __future__ import annotations

from monitor.allocation import STATUS_ABAIXO, STATUS_ACIMA, AssetStatus, RebalanceAction

STATUS_LABEL = {
    STATUS_ABAIXO: "🔵 abaixo da banda",
    STATUS_ACIMA: "🔴 acima da banda",
    "ok": "✅ dentro da banda",
}

IR_NOTE = (
    "Lembrete: venda pode gerar IR (isenções e alíquotas variam por tipo de "
    "ativo — confira antes de vender)."
)


def _cotas(qty: int) -> str:
    return "1 cota" if qty == 1 else f"{qty} cotas"


def _position_lines(statuses: list[AssetStatus], show_values: bool) -> list[str]:
    lines = []
    for s in statuses:
        detalhe = f"{_cotas(s.qty)} × R$ {s.price:.2f} = R$ {s.value:,.2f} (" if show_values else "("
        lines.append(
            f"{s.ticker}: {detalhe}{s.pct:.1%} — alvo {s.target.target:.0%}, "
            f"banda {s.target.min:.0%}-{s.target.max:.0%}) {STATUS_LABEL[s.status]}"
        )
    return lines


def _actions_section(
    actions: list[RebalanceAction],
    contribution_weights: dict[str, float],
    aporte_fix: dict[str, float] | None,
) -> list[str]:
    if not actions:
        lines = ["✅ Todos os ativos dentro da banda. Nenhuma venda necessária.", ""]
        lines.append("Sugestão de destino do próximo aporte:")
        for ticker, weight in sorted(contribution_weights.items(), key=lambda kv: -kv[1]):
            if weight > 0:
                lines.append(f"- {ticker}: {weight:.0%}")
        return lines

    tem_venda = any(a.action == "vender" for a in actions)

    if not tem_venda:
        # Só tem "comprar" no plano — os ativos que sobram já estão dentro
        # da própria banda, então isso já é, na prática, um aporte (dinheiro
        # novo), sem venda nem IR envolvidos.
        lines = ["🟡 *Aporte necessário* (nenhuma venda envolvida):", ""]
        for a in actions:
            lines.append(f"- Comprar {_cotas(a.qty)} de {a.ticker} (aprox. R$ {a.approx_value:,.2f})")
        return lines

    lines = ["⚠️ *Rebalanceamento necessário*", ""]

    if aporte_fix:
        lines.append("Opção 1 — resolve só com aporte, sem vender nada:")
        for ticker, valor in sorted(aporte_fix.items(), key=lambda kv: -kv[1]):
            lines.append(f"- Aportar R$ {valor:,.2f} em {ticker}")
        lines.append("")
        lines.append("Opção 2 (alternativa) — venda + compra:")
    else:
        lines.append("Não dá pra resolver só com aporte (precisaria de um aporte grande "
                      "demais). Venda recomendada:")

    for a in actions:
        lines.append(f"- {a.action.upper()} {_cotas(a.qty)} de {a.ticker} (aprox. R$ {a.approx_value:,.2f})")
    lines.append("")
    lines.append(IR_NOTE)
    return lines


def build_report(
    statuses: list[AssetStatus],
    actions: list[RebalanceAction],
    contribution_weights: dict[str, float],
    quotas_metadata: dict,
    aporte_fix: dict[str, float] | None = None,
    *,
    show_values: bool = True,
) -> str:
    lines = ["📊 *Monitor de Carteira*", ""]
    lines.extend(_position_lines(statuses, show_values))
    lines.append("")

    if show_values:
        total = sum(s.value for s in statuses)
        lines.append(f"Valor total: R$ {total:,.2f}")
    lines.append(f"Posição atualizada em: {quotas_metadata.get('updated_at')} (fonte: {quotas_metadata.get('source')})")
    lines.append("")

    lines.extend(_actions_section(actions, contribution_weights, aporte_fix))

    return "\n".join(lines)
