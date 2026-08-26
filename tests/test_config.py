import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from monitor.config import (
    append_history,
    append_wealth_history,
    load_last_status,
    load_portfolio,
    load_wealth_history,
    save_last_status,
)


def _write_portfolio(path: Path, banda_pp: float, targets: dict[str, float]) -> None:
    data = {"banda_pp": banda_pp, "assets": {ticker: {"target": t} for ticker, t in targets.items()}}
    path.write_text(yaml.safe_dump(data), encoding="utf-8")


def test_load_portfolio_deriva_min_max_do_banda_pp(tmp_path):
    path = tmp_path / "portfolio.yaml"
    _write_portfolio(path, banda_pp=0.15, targets={"B5P211": 0.40, "VWRA11": 0.30, "DIVO11": 0.30})

    assets = load_portfolio(path)

    assert assets["B5P211"].min == pytest.approx(0.25)
    assert assets["B5P211"].max == pytest.approx(0.55)
    assert assets["VWRA11"].min == pytest.approx(0.15)
    assert assets["VWRA11"].max == pytest.approx(0.45)


def test_load_portfolio_recorta_min_em_zero_e_max_em_um(tmp_path):
    path = tmp_path / "portfolio.yaml"
    # target de 5% com banda de 15pp geraria min negativo (-10%) sem o recorte.
    _write_portfolio(path, banda_pp=0.15, targets={"GOLD11": 0.05, "B5P211": 0.95})

    assets = load_portfolio(path)

    assert assets["GOLD11"].min == 0.0
    assert assets["B5P211"].max == 1.0


def test_load_portfolio_muda_so_editando_banda_pp(tmp_path):
    """Trocar a largura da banda de toda a carteira é editar 1 número."""
    path = tmp_path / "portfolio.yaml"
    targets = {"B5P211": 0.40, "VWRA11": 0.30, "DIVO11": 0.30}

    _write_portfolio(path, banda_pp=0.15, targets=targets)
    banda_15 = load_portfolio(path)

    _write_portfolio(path, banda_pp=0.10, targets=targets)
    banda_10 = load_portfolio(path)

    assert banda_15["B5P211"].max - banda_15["B5P211"].min == pytest.approx(0.30)
    assert banda_10["B5P211"].max - banda_10["B5P211"].min == pytest.approx(0.20)


def test_load_portfolio_falha_sem_banda_pp(tmp_path):
    path = tmp_path / "portfolio.yaml"
    path.write_text(yaml.safe_dump({"assets": {"B5P211": {"target": 1.0}}}), encoding="utf-8")

    with pytest.raises(ValueError, match="banda_pp"):
        load_portfolio(path)


def test_load_portfolio_falha_com_banda_pp_fora_do_intervalo(tmp_path):
    path = tmp_path / "portfolio.yaml"
    _write_portfolio(path, banda_pp=1.5, targets={"B5P211": 1.0})

    with pytest.raises(ValueError, match="banda_pp"):
        load_portfolio(path)


def test_load_portfolio_falha_quando_targets_nao_somam_100_por_cento(tmp_path):
    path = tmp_path / "portfolio.yaml"
    _write_portfolio(path, banda_pp=0.15, targets={"B5P211": 0.40, "VWRA11": 0.30})

    with pytest.raises(ValueError, match="somar 100%"):
        load_portfolio(path)


def test_load_last_status_sem_arquivo_retorna_vazio(tmp_path):
    assert load_last_status(tmp_path / "nao-existe.yaml") == {}


def test_save_e_load_last_status_faz_round_trip(tmp_path):
    path = tmp_path / "last_status.yaml"
    status = {"B5P211": "ok", "VWRA11": "abaixo_da_banda"}
    save_last_status(status, path)
    assert load_last_status(path) == status


def test_append_history_cria_cabecalho_e_acumula_linhas(tmp_path):
    path = tmp_path / "history.csv"
    append_history({"B5P211": 0.40, "VWRA11": 0.29}, path)
    append_history({"B5P211": 0.41, "VWRA11": 0.30}, path)

    lines = path.read_text(encoding="utf-8").strip().splitlines()
    assert lines[0] == "timestamp_utc,B5P211,VWRA11"
    assert len(lines) == 3  # cabeçalho + 2 linhas
    assert lines[1].endswith("0.4000,0.2900")
    assert lines[2].endswith("0.4100,0.3000")


def test_load_wealth_history_sem_arquivo_retorna_vazio(tmp_path):
    assert load_wealth_history(tmp_path / "nao-existe.csv") == []


def test_append_wealth_history_acumula_e_ordena(tmp_path):
    path = tmp_path / "wealth_history.csv"
    append_wealth_history(
        {"date": "2026-02-01", "wealth": "1100", "invested": "1000", "nominal_return": "0.10", "real_return": "0.08"},
        path,
    )
    append_wealth_history(
        {"date": "2026-01-01", "wealth": "1000", "invested": "1000", "nominal_return": "0.0", "real_return": "0.0"},
        path,
    )
    rows = load_wealth_history(path)
    assert [r["date"] for r in rows] == ["2026-01-01", "2026-02-01"]


def test_append_wealth_history_substitui_linha_do_mesmo_dia(tmp_path):
    path = tmp_path / "wealth_history.csv"
    append_wealth_history(
        {"date": "2026-01-01", "wealth": "1000", "invested": "1000", "nominal_return": "0.0", "real_return": "0.0"},
        path,
    )
    append_wealth_history(
        {"date": "2026-01-01", "wealth": "1050", "invested": "1000", "nominal_return": "0.05", "real_return": "0.04"},
        path,
    )
    rows = load_wealth_history(path)
    assert len(rows) == 1
    assert rows[0]["wealth"] == "1050"
