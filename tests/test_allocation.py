import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from monitor.allocation import (
    STATUS_ABAIXO,
    STATUS_ACIMA,
    STATUS_OK,
    compute_statuses,
    contribution_suggestion,
    effective_status_for_alerting,
    rebalance_plan,
    resolve_via_aporte,
)
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


def test_resolve_via_aporte_none_quando_tudo_ok():
    prices = {t: 100.0 for t in TARGETS}
    holdings = {"B5P211": 40, "VWRA11": 30, "DIVO11": 20, "CDIB11": 5, "GOLD11": 5}
    statuses = compute_statuses(holdings, prices, TARGETS)
    assert resolve_via_aporte(statuses) is None


def test_resolve_via_aporte_calcula_valor_que_resolve_o_breach():
    # só VWRA11 abaixo do piso de 30%; os demais com folga acima do
    # próprio piso, então diluí-los um pouco pra corrigir VWRA11 não
    # quebra mais nada.
    prices = {t: 100.0 for t in TARGETS}
    holdings = {"B5P211": 40, "VWRA11": 26, "DIVO11": 22, "CDIB11": 6, "GOLD11": 6}
    statuses = compute_statuses(holdings, prices, TARGETS)
    assert any(s.status != STATUS_OK for s in statuses)

    aporte = resolve_via_aporte(statuses)
    assert aporte is not None
    assert sum(aporte.values()) > 0

    # simula aplicar o aporte e confirma que tudo fica dentro da banda
    total = sum(s.value for s in statuses)
    novo_total = total + sum(aporte.values())
    for s in statuses:
        novo_valor = s.value + aporte.get(s.ticker, 0.0)
        novo_pct = novo_valor / novo_total
        assert s.target.min - 1e-6 <= novo_pct <= s.target.max + 1e-6


def test_resolve_via_aporte_none_quando_diluir_quebraria_outro_ativo():
    # cenário real: 3 ativos abaixo do alvo (VWRA11, DIVO11, GOLD11), mas
    # diluir o suficiente pra corrigi-los derruba o CDIB11 (hoje ok, perto
    # do próprio piso de 5%) pra fora da banda antes disso — não dá pra
    # resolver só com aporte, é preciso vender/rebalancear.
    prices = {"B5P211": 110.63, "VWRA11": 114.28, "DIVO11": 122.43, "CDIB11": 51.57, "GOLD11": 24.69}
    holdings = {"B5P211": 65, "VWRA11": 46, "DIVO11": 29, "CDIB11": 24, "GOLD11": 36}
    statuses = compute_statuses(holdings, prices, TARGETS)
    assert resolve_via_aporte(statuses) is None


def test_effective_status_segura_recuperacao_perto_da_borda():
    prices = {t: 100.0 for t in TARGETS}
    # VWRA11 bem em cima do piso (30.2%, dentro por pouco)
    holdings = {"B5P211": 39, "VWRA11": 30.2, "DIVO11": 20, "CDIB11": 5.4, "GOLD11": 5.4}
    statuses = compute_statuses(holdings, prices, TARGETS)
    vwra = next(s for s in statuses if s.ticker == "VWRA11")
    assert vwra.status == STATUS_OK  # real: já voltou pra dentro da banda

    last_status = {s.ticker: s.status for s in statuses}
    last_status["VWRA11"] = STATUS_ABAIXO  # última vez que alertamos, estava abaixo

    effective = effective_status_for_alerting(statuses, last_status, hysteresis=0.01)
    assert effective["VWRA11"] == STATUS_ABAIXO  # ainda não recuperou com margem


def test_effective_status_entra_em_banda_na_hora_sem_atraso():
    prices = {t: 100.0 for t in TARGETS}
    holdings = {"B5P211": 70, "VWRA11": 15, "DIVO11": 10, "CDIB11": 2, "GOLD11": 3}
    statuses = compute_statuses(holdings, prices, TARGETS)
    last_status = {s.ticker: STATUS_OK for s in statuses}

    effective = effective_status_for_alerting(statuses, last_status, hysteresis=0.01)
    assert effective["B5P211"] == STATUS_ACIMA  # entrada em breach é imediata
