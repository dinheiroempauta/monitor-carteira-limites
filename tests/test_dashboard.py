import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from monitor.allocation import compute_statuses
from monitor.config import AssetTarget
from monitor import dashboard
from monitor.dashboard import build_dashboard_html
from monitor.performance import MonthlyReturn

TARGETS = {
    "B5P211": AssetTarget("B5P211", target=0.40, min=0.20, max=0.50),
    "VWRA11": AssetTarget("VWRA11", target=0.30, min=0.30, max=0.50),
}


def _extract_dados(html: str) -> dict:
    marker = "const dados = "
    start = html.index(marker) + len(marker)
    end = html.index(";\n", start)
    return json.loads(html[start:end])


def test_build_dashboard_html_embute_composicao_patrimonio_e_performance():
    holdings = {"B5P211": 10, "VWRA11": 5}
    prices = {"B5P211": 100.0, "VWRA11": 100.0}
    statuses = compute_statuses(holdings, prices, TARGETS)

    wealth_history = [
        {"date": "2026-01-01", "wealth": "1000.0", "invested": "1000.0", "nominal_return": "0.0", "real_return": ""},
        {"date": "2026-02-01", "wealth": "1100.0", "invested": "1000.0", "nominal_return": "0.10", "real_return": "0.08"},
    ]
    monthly_returns = [
        MonthlyReturn(year=2026, month=1, nominal=0.10, real=0.08),
        MonthlyReturn(year=2026, month=2, nominal=0.02, real=None),
    ]

    html = build_dashboard_html(statuses, wealth_history, monthly_returns, generated_at="2026-08-24 10:00")

    assert "<html" in html
    assert "2026-08-24 10:00" in html

    dados = _extract_dados(html)
    b5p211 = next(a for a in dados["composicao"] if a["ticker"] == "B5P211")
    assert b5p211["pct"] == round(1000 / 1500 * 100, 2)
    assert b5p211["alvo"] == 40.0
    assert b5p211["min"] == 20.0
    assert b5p211["max"] == 50.0
    assert b5p211["status"] == "acima_da_banda"  # 1000/1500=66.7%, acima do teto de 50%
    assert dados["patrimonio"] == [
        {"data": "2026-01-01", "valor": 1000.0},
        {"data": "2026-02-01", "valor": 1100.0},
    ]
    assert dados["performance"] == [
        {"mes": "jan/2026", "nominal": 10.0, "real": 8.0},
        {"mes": "fev/2026", "nominal": 2.0, "real": None},
    ]


def test_build_dashboard_html_nao_inclui_formulario_por_padrao():
    """Formulário desativado (SHOW_TRANSACTION_FORM=False) desde que o
    registro de transação passou a ser automático via e-mail — ver
    specs/003-importacao-automatica-notas/. Código do formulário
    permanece em dashboard.py, só não é renderizado."""
    holdings = {"B5P211": 10, "VWRA11": 5}
    prices = {"B5P211": 100.0, "VWRA11": 100.0}
    statuses = compute_statuses(holdings, prices, TARGETS)

    html = build_dashboard_html(statuses, [], [], generated_at="2026-08-24 10:00")

    assert 'id="tx-form"' not in html
    assert 'id="gh-token-input"' not in html
    # abas/chaves balanceadas — formatação do template não deixou nada sem substituir
    assert html.count("{{") == 0 and "{dados_json}" not in html and "{form_section}" not in html


def test_build_dashboard_html_formulario_disponivel_se_reativado():
    """SHOW_TRANSACTION_FORM=True continua funcional — só desativado por padrão."""
    holdings = {"B5P211": 10, "VWRA11": 5}
    prices = {"B5P211": 100.0, "VWRA11": 100.0}
    statuses = compute_statuses(holdings, prices, TARGETS)

    original = dashboard.SHOW_TRANSACTION_FORM
    dashboard.SHOW_TRANSACTION_FORM = True
    try:
        html = build_dashboard_html(statuses, [], [], generated_at="2026-08-24 10:00")
    finally:
        dashboard.SHOW_TRANSACTION_FORM = original

    assert 'id="tx-form"' in html
    assert 'id="gh-token-input"' in html
    assert '"dinheiroempauta"' in html
    assert '"monitor-carteira-limites"' in html
    assert "config/transactions.csv" in html
    assert html.count("{{") == 0 and "{dados_json}" not in html
