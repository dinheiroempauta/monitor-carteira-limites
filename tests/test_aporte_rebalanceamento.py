import importlib.util
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

_spec = importlib.util.spec_from_file_location(
    "aporte_rebalanceamento", REPO_ROOT / "scripts" / "aporte_rebalanceamento.py"
)
aporte_rebalanceamento = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(aporte_rebalanceamento)


def test_checar_frescor_aceita_timestamp_recente():
    run_timestamp = datetime.now(timezone.utc) - timedelta(minutes=5)
    idade = aporte_rebalanceamento.checar_frescor(run_timestamp, max_idade_minutos=30)
    assert 4 <= idade <= 6


def test_checar_frescor_recusa_timestamp_velho():
    run_timestamp = datetime.now(timezone.utc) - timedelta(hours=2)
    with pytest.raises(SystemExit):
        aporte_rebalanceamento.checar_frescor(run_timestamp, max_idade_minutos=30)


def test_checar_frescor_recusa_timestamp_no_futuro():
    # Sinal de que alguém copiou o horário errado do log — nunca deve passar.
    run_timestamp = datetime.now(timezone.utc) + timedelta(minutes=10)
    with pytest.raises(SystemExit):
        aporte_rebalanceamento.checar_frescor(run_timestamp, max_idade_minutos=30)


def test_parse_timestamp_aceita_sufixo_z():
    dt = aporte_rebalanceamento.parse_timestamp("2026-08-25T16:19:59Z")
    assert dt.tzinfo is not None
    assert dt.year == 2026 and dt.hour == 16


def test_parse_timestamp_rejeita_formato_invalido():
    with pytest.raises(SystemExit):
        aporte_rebalanceamento.parse_timestamp("25/08/2026 16:19")
