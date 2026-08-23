"""Diagnóstico temporário: testa cada ticker individualmente contra a API
HG Brasil e imprime a resposta bruta, para descobrir se a restrição de
plano é por ticker (ex.: ETFs/FIIs menos líquidos) ou pelo endpoint como
um todo. PETR4 entra como controle (ação líquida, deveria estar liberada
em qualquer plano)."""
import os

import requests

TICKERS = ["PETR4", "B5P211", "VWRA11", "DIVO11", "CDIB11", "GOLD11"]


def main():
    key = os.environ["HGBRASIL_KEY"]
    for ticker in TICKERS:
        response = requests.get(
            "https://api.hgbrasil.com/finance/stock_price",
            params={"key": key, "symbol": ticker},
            timeout=15,
        )
        print(f"{ticker}: status={response.status_code} body={response.json()}")


if __name__ == "__main__":
    main()
