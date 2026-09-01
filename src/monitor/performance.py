"""Calcula performance nominal e real (descontada a inflação). Funções
puras — sem I/O — para serem fáceis de testar.

Duas granularidades:
- `compute_nominal_return`/`compute_real_return`: um único ponto no tempo
  (hoje), acumulado desde o início do acompanhamento — usado nos KPIs do
  topo do dashboard.
- `compute_monthly_returns`: retorno de CADA MÊS isoladamente (nominal e
  real, descontando só a inflação daquele mês) — usado no gráfico de
  barras de performance mensal.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from monitor.ipca import accumulated_index


def compute_nominal_return(wealth: float, invested: float) -> float:
    """Retorno nominal (ex.: 0.05 = +5%) — patrimônio atual vs. total
    investido até agora."""
    if invested <= 0:
        return 0.0
    return wealth / invested - 1


def compute_real_return(nominal_return: float, ipca_monthly: list[tuple[date, float]]) -> float | None:
    """Retorno real, descontando o IPCA acumulado nos meses informados em
    `ipca_monthly` — o chamador é responsável por já ter filtrado essa
    lista para conter só os meses relevantes (ex.: a partir do mês da
    primeira transação; incluir meses de antes do início do
    acompanhamento infla artificialmente o desconto). `None` se não houver
    dado de IPCA disponível."""
    if not ipca_monthly:
        return None
    indice = accumulated_index(ipca_monthly)
    return (1 + nominal_return) / indice - 1


@dataclass(frozen=True)
class MonthlyReturn:
    year: int
    month: int  # 1-12
    nominal: float | None  # None só se não houver capital em risco no mês (denominador zero)
    real: float | None  # None se o IPCA daquele mês ainda não foi publicado


def compute_monthly_returns(
    daily_points: list[tuple[date, float, float]],
    ipca_by_month: dict[tuple[int, int], float],
) -> list[MonthlyReturn]:
    """Retorno nominal e real de cada mês calendário, isoladamente — não
    acumulado com os meses anteriores.

    `daily_points` é a série diária (data, patrimônio, total_investido) já
    coletada em config/wealth_history.csv, em qualquer ordem. Para cada
    mês, usa o ÚLTIMO ponto do mês como o "fechamento" dele (funciona tanto
    para um mês encerrado quanto para o mês corrente, ainda em andamento —
    nesse caso o valor muda a cada execução até o mês fechar).

    Fórmula (retorno sobre o capital em risco no mês, isolando o efeito de
    aporte/resgate — uma aproximação simples: assume que o dinheiro
    aportado durante o mês rendeu o mês inteiro, não só a partir do dia do
    aporte):

        ganho_do_mês = patrimônio_fim − patrimônio_início − aporte_líquido_do_mês
        capital_em_risco = patrimônio_início + aporte_líquido_do_mês
        nominal_do_mês = ganho_do_mês / capital_em_risco

    `patrimônio_início` e o "total investido" de início de mês vêm do
    fechamento do mês anterior.

    O PRIMEIRO mês calendário da série NUNCA aparece no resultado: ele não
    tem um "fechamento do mês anterior" de verdade pra comparar (só há uma
    aproximação de patrimônio/investido = 0, como se a carteira tivesse
    nascido exatamente no dia 1 daquele mês — o que raramente é o caso: o
    usuário normalmente já vinha investindo dias/semanas antes do dashboard
    começar a coletar dados). Ele só serve de baseline silenciosa para
    calcular o retorno do mês seguinte, que aí sim compara fechamento
    contra fechamento (dado real, não aproximado). Com só 1 mês de dados,
    o resultado fica vazio.

    O retorno real de cada mês desconta só o IPCA DAQUELE mês (não
    acumulado com outros meses) — `ipca_by_month` mapeia (ano, mês) para a
    variação percentual mensal (ex.: 0.42 = 0.42%). Mês sem IPCA publicado
    ainda vira `real=None` (nunca é tratado como 0%).
    """
    if not daily_points:
        return []

    by_month: dict[tuple[int, int], list[tuple[date, float, float]]] = {}
    for d, wealth, invested in daily_points:
        by_month.setdefault((d.year, d.month), []).append((d, wealth, invested))

    results = []
    prev_wealth = 0.0
    prev_invested = 0.0
    for i, key in enumerate(sorted(by_month)):
        rows = sorted(by_month[key], key=lambda r: r[0])
        _, wealth_end, invested_end = rows[-1]

        if i > 0:  # primeiro mês nunca entra no resultado — só define a base do 2º
            aporte_liquido = invested_end - prev_invested
            capital_em_risco = prev_wealth + aporte_liquido
            if abs(capital_em_risco) < 1e-9:
                nominal = None
            else:
                nominal = (wealth_end - prev_wealth - aporte_liquido) / capital_em_risco

            ipca_mes = ipca_by_month.get(key)
            real = None
            if nominal is not None and ipca_mes is not None:
                real = (1 + nominal) / (1 + ipca_mes / 100) - 1

            results.append(MonthlyReturn(year=key[0], month=key[1], nominal=nominal, real=real))

        prev_wealth, prev_invested = wealth_end, invested_end

    return results
