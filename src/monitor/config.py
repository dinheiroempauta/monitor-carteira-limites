"""Carrega e valida a configuração de alocação-alvo e a posição atual."""
from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
PORTFOLIO_PATH = REPO_ROOT / "config" / "portfolio.yaml"
QUOTAS_PATH = REPO_ROOT / "config" / "quotas.yaml"
LAST_STATUS_PATH = REPO_ROOT / "config" / "last_status.yaml"
HISTORY_PATH = REPO_ROOT / "config" / "history.csv"


@dataclass(frozen=True)
class AssetTarget:
    ticker: str
    target: float
    min: float
    max: float


def load_portfolio(path: Path = PORTFOLIO_PATH) -> dict[str, AssetTarget]:
    data = yaml.safe_load(path.read_text())
    assets = {}
    for ticker, cfg in data["assets"].items():
        target = AssetTarget(ticker=ticker, target=cfg["target"], min=cfg["min"], max=cfg["max"])
        if not (0 <= target.min <= target.target <= target.max <= 1):
            raise ValueError(f"Banda inválida para {ticker}: min/target/max devem satisfazer 0<=min<=target<=max<=1")
        assets[ticker] = target
    total_target = sum(a.target for a in assets.values())
    if abs(total_target - 1.0) > 1e-6:
        raise ValueError(f"Os targets devem somar 100%, somaram {total_target:.2%}")
    return assets


def load_quotas(path: Path = QUOTAS_PATH) -> dict[str, int]:
    data = yaml.safe_load(path.read_text())
    return {ticker: int(qty) for ticker, qty in data["holdings"].items()}


def load_quotas_metadata(path: Path = QUOTAS_PATH) -> dict:
    data = yaml.safe_load(path.read_text())
    return {"updated_at": data.get("updated_at"), "source": data.get("source", "manual")}


def load_last_status(path: Path = LAST_STATUS_PATH) -> dict[str, str]:
    """Status (por ticker) salvo na última execução que gerou alerta.
    Arquivo ausente = nunca alertamos antes (retorna vazio)."""
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text()) or {}
    return dict(data)


def save_last_status(status_by_ticker: dict[str, str], path: Path = LAST_STATUS_PATH) -> None:
    path.write_text(yaml.safe_dump(status_by_ticker, allow_unicode=True, sort_keys=True), encoding="utf-8")


def append_history(pct_by_ticker: dict[str, float], path: Path = HISTORY_PATH) -> None:
    """Acrescenta uma linha ao histórico de alocação (só percentuais — sem
    valor em R$, de propósito, pra não virar um registro de quanto dinheiro
    tem). Cria o arquivo com cabeçalho se ainda não existir."""
    tickers = sorted(pct_by_ticker)
    is_new = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if is_new:
            writer.writerow(["timestamp_utc", *tickers])
        timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
        writer.writerow([timestamp, *(f"{pct_by_ticker[t]:.4f}" for t in tickers)])
