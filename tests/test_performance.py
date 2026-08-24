import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from monitor.performance import compute_nominal_return, compute_real_return


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
