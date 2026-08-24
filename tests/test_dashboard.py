import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from monitor.allocation import compute_statuses
from monitor.config import AssetTarget
from monitor.dashboard import build_dashboard_html
from monitor.performance import PerformancePoint

TARGETS = {
    "B5P211": AssetTarget("B5P211", target=0.40, min=0.20, max=0.50),
    "VWRA11": AssetTarget("VWRA11", target=0.30, min=0.30, max=0.50),
}


def _extract_dados(html: str) -> dict:
    marker = "const dados = "
    start = html.index(marker) + len(marker)
    end = html.index(";\n", start)
    return json.loads(html[start:end])


def test_build_dashboard_html_embute_composicao_patrimonio_e_performance():
    holdings = {"B5P211": 10, "VWRA11": 5}
    prices = {"B5P211": 100.0, "VWRA11": 100.0}
    statuses = compute_statuses(holdings, prices, TARGETS)

    performance_points = [
        PerformancePoint(date(2026, 1, 1), wealth=1000.0, invested=1000.0, nominal_return=0.0, real_return=None),
        PerformancePoint(date(2026, 2, 1), wealth=1100.0, invested=1000.0, nominal_return=0.10, real_return=0.08),
    ]

    html = build_dashboard_html(statuses, performance_points, generated_at="2026-08-24 10:00")

    assert "<html" in html
    assert "2026-08-24 10:00" in html

    dados = _extract_dados(html)
    assert {"ticker": "B5P211", "pct": round(1000 / 1500 * 100, 2)} in dados["composicao"]
    assert dados["patrimonio"] == [
        {"data": "2026-01-01", "valor": 1000.0},
        {"data": "2026-02-01", "valor": 1100.0},
    ]
    assert dados["performance"][1] == {"data": "2026-02-01", "nominal": 10.0, "real": 8.0}
    assert dados["performance"][0]["real"] is None
