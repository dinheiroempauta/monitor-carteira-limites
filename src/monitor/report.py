"""Monta o texto do relatório em pt-BR a partir dos cálculos de alocação."""
from __future__ import annotations

from monitor.allocation import STATUS_ABAIXO, STATUS_ACIMA, AssetStatus, RebalanceAction

STATUS_LABEL = {
    STATUS_ABAIXO: "🔵 abaixo da banda",
    STATUS_ACIMA: "🔴 acima da banda",
    "ok": "✅ dentro da banda",
}


def build_report(
    statuses: list[AssetStatus],
    actions: list[RebalanceAction],
    contribution_weights: dict[str, float],
    quotas_metadata: dict,
) -> str:
    total = sum(s.value for s in statuses)
    lines = ["📊 *Monitor de Carteira*", ""]

    for s in statuses:
        lines.append(
            f"{s.ticker}: {s.qty} cotas × R$ {s.price:.2f} = R$ {s.value:,.2f} "
            f"({s.pct:.1%} — alvo {s.target.target:.0%}, banda {s.target.min:.0%}-{s.target.max:.0%}) "
            f"{STATUS_LABEL[s.status]}"
        )

    lines.append("")
    lines.append(f"Valor total: R$ {total:,.2f}")
    lines.append(f"Posição atualizada em: {quotas_metadata.get('updated_at')} (fonte: {quotas_metadata.get('source')})")
    lines.append("")

    if actions:
        lines.append("⚠️ *Rebalanceamento necessário — venda recomendada:*")
        for a in actions:
            lines.append(f"- {a.action.upper()} {a.qty} cotas de {a.ticker} (aprox. R$ {a.approx_value:,.2f})")
    else:
        lines.append("✅ Todos os ativos dentro da banda. Nenhuma venda necessária.")
        lines.append("")
        lines.append("Sugestão de destino do próximo aporte:")
        for ticker, weight in sorted(contribution_weights.items(), key=lambda kv: -kv[1]):
            if weight > 0:
                lines.append(f"- {ticker}: {weight:.0%}")

    return "\n".join(lines)
