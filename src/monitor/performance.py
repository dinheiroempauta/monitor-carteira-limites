"""Calcula performance nominal e real (descontada a inflação) num único
ponto no tempo — hoje. Não reconstrói o passado (sem histórico de preço);
o dashboard acumula um ponto por dia daqui pra frente, em config/wealth_history.csv.
Funções puras — sem I/O — para serem fáceis de testar.
"""
from __future__ import annotations

from datetime import date

from monitor.ipca import accumulated_index


def compute_nominal_return(wealth: float, invested: float) -> float:
    """Retorno nominal (ex.: 0.05 = +5%) — patrimônio atual vs. total
    investido até agora."""
    if invested <= 0:
        return 0.0
    return wealth / invested - 1


def compute_real_return(nominal_return: float, ipca_monthly: list[tuple[date, float]]) -> float | None:
    """Retorno real, descontando o IPCA acumulado desde o início do
    acompanhamento. `None` se não houver dado de IPCA disponível."""
    if not ipca_monthly:
        return None
    indice = accumulated_index(ipca_monthly)
    return (1 + nominal_return) / indice - 1
