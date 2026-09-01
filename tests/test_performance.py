import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from monitor.performance import compute_monthly_returns, compute_nominal_return, compute_real_return


def test_compute_nominal_return():
    assert abs(compute_nominal_return(wealth=1210.0, invested=1000.0) - 0.21) < 1e-9


def test_compute_nominal_return_sem_investimento_e_zero():
    assert compute_nominal_return(wealth=0.0, invested=0.0) == 0.0


def test_compute_real_return_sem_ipca_e_none():
    assert compute_real_return(0.21, []) is None


def test_compute_real_return_desconta_inflacao():
    ipca_monthly = [(date(2026, 1, 1), 1.0), (date(2026, 2, 1), 1.0), (date(2026, 3, 1), 1.0)]
    real = compute_real_return(0.21, ipca_monthly)
    indice = 1.01**3
    assert abs(real - (1.21 / indice - 1)) < 1e-9


def test_compute_monthly_returns_lista_vazia():
    assert compute_monthly_returns([], {}) == []


def test_compute_monthly_returns_primeiro_mes_nunca_aparece_no_resultado():
    """O primeiro mês da série não tem um fechamento anterior de verdade
    pra comparar (só uma aproximação de patrimônio/investido = 0) — nunca
    entra no resultado, só serve de base pro cálculo do mês seguinte. Com
    só 1 mês de dados, o resultado fica vazio."""
    daily_points = [
        (date(2026, 8, 4), 1000.0, 1000.0),
        (date(2026, 8, 31), 1050.0, 1000.0),
    ]
    assert compute_monthly_returns(daily_points, {}) == []


def test_compute_monthly_returns_segundo_mes_isola_aporte_do_ganho():
    """Aporte de 200 em setembro não deve ser contado como retorno — só o
    ganho de mercado (50) sobre o capital em risco (1000 do fim de agosto
    + 200 aportados = 1200). Agosto (primeiro mês da série) não aparece no
    resultado — só setembro, o primeiro mês com fechamento anterior real."""
    daily_points = [
        (date(2026, 8, 31), 1000.0, 1000.0),
        (date(2026, 9, 30), 1250.0, 1200.0),  # +200 aporte, +50 ganho de mercado
    ]
    result = compute_monthly_returns(daily_points, {})
    assert len(result) == 1
    setembro = result[0]
    assert setembro.year == 2026 and setembro.month == 9
    # ganho=1250-1000-200=50; capital_em_risco=1000+200=1200
    assert abs(setembro.nominal - 50 / 1200) < 1e-9


def test_compute_monthly_returns_desconta_so_o_ipca_daquele_mes():
    daily_points = [
        (date(2026, 8, 31), 1000.0, 1000.0),
        (date(2026, 9, 30), 1200.0, 1000.0),  # 20% nominal em setembro, sem aporte
    ]
    ipca_by_month = {(2026, 7): 5.0, (2026, 9): 0.5}  # julho não deve entrar na conta
    result = compute_monthly_returns(daily_points, ipca_by_month)
    setembro = result[0]
    assert abs(setembro.nominal - 0.20) < 1e-9
    assert abs(setembro.real - (1.20 / 1.005 - 1)) < 1e-9


def test_compute_monthly_returns_ipca_do_mes_nao_publicado_e_none():
    daily_points = [
        (date(2026, 8, 31), 1000.0, 1000.0),
        (date(2026, 9, 1), 1000.0, 1000.0),
    ]
    result = compute_monthly_returns(daily_points, {})
    assert len(result) == 1
    assert result[0].real is None


def test_compute_monthly_returns_usa_ultimo_ponto_do_mes_em_andamento():
    """Mês corrente (ainda sem fechar): usa o ponto mais recente disponível
    naquele mês, não o primeiro — o valor muda a cada execução até fechar."""
    daily_points = [
        (date(2026, 8, 31), 1000.0, 1000.0),
        (date(2026, 9, 1), 1000.0, 1000.0),
        (date(2026, 9, 15), 1100.0, 1000.0),
    ]
    result = compute_monthly_returns(daily_points, {})
    assert len(result) == 1
    assert abs(result[0].nominal - 0.10) < 1e-9  # usa o ponto do dia 15, não do dia 1
