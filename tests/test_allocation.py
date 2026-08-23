import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from monitor.allocation import compute_statuses, contribution_suggestion, rebalance_plan
from monitor.config import AssetTarget

TARGETS = {
    "B5P211": AssetTarget("B5P211", target=0.40, min=0.20, max=0.50),
    "VWRA11": AssetTarget("VWRA11", target=0.30, min=0.30, max=0.50),
    "DIVO11": AssetTarget("DIVO11", target=0.20, min=0.20, max=0.40),
    "CDIB11": AssetTarget("CDIB11", target=0.05, min=0.05, max=0.15),
    "GOLD11": AssetTarget("GOLD11", target=0.05, min=0.05, max=0.10),
}


def test_tudo_dentro_da_banda_nao_gera_venda():
    # posição exatamente no alvo (preço 100 para todos, valor total 1000)
    holdings = {"B5P211": 4, "VWRA11": 3, "DIVO11": 2, "CDIB11": 0.5, "GOLD11": 0.5}
    holdings = {k: v for k, v in holdings.items()}  # ints normalmente, mas ok para teste
    prices = {t: 100.0 for t in TARGETS}
    statuses = compute_statuses(holdings, prices, TARGETS)
    assert rebalance_plan(statuses) == []


def test_ativo_acima_do_teto_gera_venda():
    # B5P211 muito acima do alvo (70% do total), estourando o teto de 50%
    prices = {t: 100.0 for t in TARGETS}
    holdings = {"B5P211": 70, "VWRA11": 15, "DIVO11": 10, "CDIB11": 2, "GOLD11": 3}
    statuses = compute_statuses(holdings, prices, TARGETS)
    actions = rebalance_plan(statuses)
    b5p211_actions = [a for a in actions if a.ticker == "B5P211"]
    assert len(b5p211_actions) == 1
    assert b5p211_actions[0].action == "vender"
    assert b5p211_actions[0].qty > 0


def test_ativo_abaixo_do_piso_gera_compra():
    # CDIB11 bem abaixo do piso de 5%
    prices = {t: 100.0 for t in TARGETS}
    holdings = {"B5P211": 40, "VWRA11": 30, "DIVO11": 20, "CDIB11": 0, "GOLD11": 10}
    statuses = compute_statuses(holdings, prices, TARGETS)
    actions = rebalance_plan(statuses)
    cdib_actions = [a for a in actions if a.ticker == "CDIB11"]
    assert len(cdib_actions) == 1
    assert cdib_actions[0].action == "comprar"


def test_sugestao_de_aporte_soma_100_por_cento_e_prioriza_maior_desvio():
    prices = {t: 100.0 for t in TARGETS}
    # tudo dentro da banda, mas CDIB11 relativamente mais abaixo do alvo
    holdings = {"B5P211": 40, "VWRA11": 30, "DIVO11": 20, "CDIB11": 5, "GOLD11": 5}
    holdings["CDIB11"] = 6  # ainda dentro da banda [5,15], mas abaixo do alvo 5%? ajusta pra baixo do alvo
    statuses = compute_statuses(holdings, prices, TARGETS)
    assert rebalance_plan(statuses) == []
    weights = contribution_suggestion(statuses)
    assert abs(sum(weights.values()) - 1.0) < 1e-9
