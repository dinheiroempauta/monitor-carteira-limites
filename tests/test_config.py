import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from monitor.config import (
    append_history,
    append_wealth_history,
    load_last_status,
    load_wealth_history,
    save_last_status,
)


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
