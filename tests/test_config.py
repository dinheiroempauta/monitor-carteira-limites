import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from monitor.config import load_last_status, save_last_status


def test_load_last_status_sem_arquivo_retorna_vazio(tmp_path):
    assert load_last_status(tmp_path / "nao-existe.yaml") == {}


def test_save_e_load_last_status_faz_round_trip(tmp_path):
    path = tmp_path / "last_status.yaml"
    status = {"B5P211": "ok", "VWRA11": "abaixo_da_banda"}
    save_last_status(status, path)
    assert load_last_status(path) == status
