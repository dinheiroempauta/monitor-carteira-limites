import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from monitor.allocation import STATUS_OK, aporte_quotas_plan, compute_statuses
from monitor.config import AssetTarget
from monitor.report import build_aporte_report

TARGETS = {
    "B5P211": AssetTarget("B5P211", target=0.40, min=0.20, max=0.50),
    "VWRA11": AssetTarget("VWRA11", target=0.30, min=0.30, max=0.50),
    "DIVO11": AssetTarget("DIVO11", target=0.20, min=0.20, max=0.40),
    "CDIB11": AssetTarget("CDIB11", target=0.05, min=0.05, max=0.15),
    "GOLD11": AssetTarget("GOLD11", target=0.05, min=0.05, max=0.10),
}


def test_build_aporte_report_mostra_todos_os_ativos_e_o_valor_do_aporte():
    prices = {"B5P211": 110.64, "VWRA11": 114.67, "DIVO11": 123.69, "CDIB11": 51.57, "GOLD11": 24.83}
    holdings = {"B5P211": 65, "VWRA11": 46, "DIVO11": 29, "CDIB11": 24, "GOLD11": 36}
    statuses = compute_statuses(holdings, prices, TARGETS)
    plan = aporte_quotas_plan(statuses, aporte=4770.13)

    relatorio = build_aporte_report(plan, statuses, aporte=4770.13)

    assert "R$ 4.770,13" in relatorio
    for ticker in TARGETS:
        assert ticker in relatorio
    # CDIB11 já está acima do alvo nesse cenário: não deve receber compra.
    assert "*CDIB11* — não comprar" in relatorio
    assert "◾" in relatorio and "→ fica em" in relatorio
    assert all(s.status == STATUS_OK for s in plan.final_statuses)
    assert "não foi suficiente" not in relatorio


def test_build_aporte_report_avisa_quando_aporte_nao_resolve_tudo():
    prices = {t: 100.0 for t in TARGETS}
    holdings = {"B5P211": 40, "VWRA11": 10, "DIVO11": 10, "CDIB11": 5, "GOLD11": 1}
    statuses = compute_statuses(holdings, prices, TARGETS)
    plan = aporte_quotas_plan(statuses, aporte=10.0)  # claramente insuficiente

    relatorio = build_aporte_report(plan, statuses, aporte=10.0)

    assert "não foi suficiente" in relatorio
