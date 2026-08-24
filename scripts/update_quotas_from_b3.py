"""Atualiza config/quotas.yaml automaticamente lendo a posição consolidada
na Área do Investidor da B3 (investidorcer.b3.com.br), que funciona para
qualquer corretora (inclui Rico) porque a custódia é sempre na B3.

EXPERIMENTAL / best-effort: o site pode mudar de layout, exigir captcha ou
bloquear automação a qualquer momento. Por isso:

- Qualquer falha aqui é capturada e vira só um log + exit code 1.
- config/quotas.yaml só é sobrescrito se a extração deu certo.
- src/monitor/main.py nunca depende deste script rodar com sucesso: ele
  sempre usa o que já estiver salvo em quotas.yaml.

Rode localmente primeiro (`python scripts/update_quotas_from_b3.py`) e só
ligue ENABLE_B3_SCRAPER=true no workflow do GitHub Actions depois de
confirmar que funciona de forma estável na sua conta — IPs de datacenter
como os do GitHub Actions costumam cair em captcha/bot-detection.

Credenciais via variáveis de ambiente B3_CPF e B3_PASSWORD (nunca no código
ou no repo).

Modo debug: rode com B3_SCRAPER_DEBUG=true para abrir o navegador visível
(não-headless) e pausar antes de fechar em caso de erro — assim dá pra ver
exatamente onde travou (login, captcha, tabela com layout diferente). Em
qualquer falha, um screenshot e o HTML da página são salvos em
scripts/.debug/ para diagnóstico.
"""
from __future__ import annotations

import os
import re
import sys
from datetime import date
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
QUOTAS_PATH = REPO_ROOT / "config" / "quotas.yaml"
DEBUG_DIR = Path(__file__).resolve().parent / ".debug"
LOGIN_URL = "https://www.investidorcer.b3.com.br/login"

# Tickers que nos interessam — usado para filtrar a tabela de posição.
TICKERS = ["B5P211", "VWRA11", "DIVO11", "CDIB11", "GOLD11"]


def _dump_debug_artifacts(page) -> None:
    """Salva screenshot + HTML da página no momento da falha, para
    diagnosticar sem precisar rodar tudo de novo."""
    DEBUG_DIR.mkdir(exist_ok=True)
    try:
        page.screenshot(path=str(DEBUG_DIR / "falha.png"), full_page=True)
        (DEBUG_DIR / "falha.html").write_text(page.content(), encoding="utf-8")
        print(f"Artefatos de diagnóstico salvos em {DEBUG_DIR}/", file=sys.stderr)
    except Exception as dump_exc:
        print(f"Não foi possível salvar artefatos de diagnóstico: {dump_exc}", file=sys.stderr)


def scrape_holdings(cpf: str, password: str, debug: bool = False) -> dict[str, int]:
    """Faz login e extrai {ticker: quantidade} da posição consolidada.

    Implementação best-effort: os seletores abaixo são um ponto de partida
    e provavelmente vão precisar de ajuste manual quando o layout do site
    mudar — é exatamente por isso que o fallback manual existe.
    """
    from playwright.sync_api import sync_playwright

    holdings: dict[str, int] = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not debug, slow_mo=250 if debug else 0)
        page = browser.new_page()
        try:
            page.goto(LOGIN_URL, timeout=30_000)
            page.fill("input[name='cpf']", cpf)
            page.fill("input[name='password']", password)
            page.click("button[type='submit']")
            page.wait_for_load_state("networkidle", timeout=30_000)

            page.goto("https://www.investidorcer.b3.com.br/posicao-consolidada", timeout=30_000)
            page.wait_for_selector("table", timeout=30_000)

            rows = page.locator("table tr").all_inner_texts()
            for row in rows:
                for ticker in TICKERS:
                    if ticker in row:
                        match = re.search(r"(\d+[\.\d]*)\s*cotas?", row, flags=re.IGNORECASE)
                        if match:
                            qty = int(match.group(1).replace(".", ""))
                            holdings[ticker] = qty
        except Exception:
            _dump_debug_artifacts(page)
            if debug:
                print("Falhou — navegador fica aberto 60s para inspeção manual (modo debug).", file=sys.stderr)
                page.wait_for_timeout(60_000)
            raise
        finally:
            browser.close()

    return holdings


def write_quotas(holdings: dict[str, int]) -> None:
    data = {
        "updated_at": date.today().isoformat(),
        "source": "b3_scraper",
        "holdings": holdings,
    }
    QUOTAS_PATH.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")


def main() -> int:
    cpf = os.environ.get("B3_CPF")
    password = os.environ.get("B3_PASSWORD")
    if not cpf or not password:
        print("B3_CPF/B3_PASSWORD não configurados — pulando scraping.", file=sys.stderr)
        return 1

    debug = os.environ.get("B3_SCRAPER_DEBUG", "").lower() == "true"

    try:
        holdings = scrape_holdings(cpf, password, debug=debug)
    except Exception as exc:  # scraping é inerentemente frágil — nunca deve derrubar o pipeline
        print(f"Scraping da B3 falhou ({exc}). Mantendo quotas.yaml existente.", file=sys.stderr)
        return 1

    missing = [t for t in TICKERS if t not in holdings]
    if missing:
        print(f"Scraping incompleto, faltando: {missing}. Mantendo quotas.yaml existente.", file=sys.stderr)
        return 1

    write_quotas(holdings)
    print(f"quotas.yaml atualizado via scraper: {holdings}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
