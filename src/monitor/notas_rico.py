"""Extração de operações de notas de negociação da Rico (e-mail + PDF).

Módulo puro (sem I/O de rede) — recebe bytes já obtidos (e-mail MIME cru,
PDF) e devolve dados estruturados. Isso separa a lógica testável (aqui) da
orquestração (busca no Gmail, chamadas à API do GitHub) que fica em
`scripts/import_notas_email.py`.
"""
from __future__ import annotations

import base64
import email
import io
import re
from email.message import Message

# Nome do produto na nota (coluna "Especificação do título") -> ticker de
# pregão. A nota não usa o ticker diretamente.
TICKER_MAP = {
    "INVESTOVWRA": "VWRA11",
    "IT NOW IDIV": "DIVO11",
    "TREND OURO": "GOLD11",
    "IT NOW B5P2": "B5P211",
    "IT NOW DIPCA": "CDIB11",
}

# A nota tem dois layouts observados para o bloco "Nr. nota / Folha / Data
# pregão": às vezes rótulo e valor se alternam linha a linha ("Data
# pregão\n18/08/2026"), às vezes os três rótulos vêm empilhados seguidos
# pelos três valores juntos numa linha de tabela ("Data pregão\n142937936 1
# 25/08/2026" — nº da nota e folha ANTES da data, na mesma linha). `\D*`
# (não-dígito) não cobre esse segundo caso, pois há dígitos (nº da
# nota/folha) entre o rótulo e a data; `.*?` com DOTALL casa qualquer coisa
# até a data mais próxima do rótulo, cobrindo os dois layouts.
_DATA_PREGAO_RE = re.compile(r"Data preg[aã]o.*?(\d{2})/(\d{2})/(\d{4})", re.DOTALL)

# Ex.: "1-BOVESPA C VISTA INVESTOVWRA CI @ 12 115,55 1.386,60 D"
#      "7-BOVESPA C VISTA IT NOW B5P2 F11 @ 11 110,32 1.213,52 D"
_OPERACAO_RE = re.compile(
    r"^\S+\s+([CV])\s+VISTA\s+(.+?)\s+(?:CI|F11)\s+@\s+(\d+)\s+([\d.,]+)\s+[\d.,]+\s+[DC]$"
)


class ProdutoNaoMapeado(Exception):
    """Produto da nota não está em TICKER_MAP — não dá para adivinhar o ticker."""

    def __init__(self, produto: str):
        self.produto = produto
        super().__init__(f"produto não mapeado: {produto!r}")


def decode_raw_email(raw_base64url: str) -> bytes:
    """Decodifica o campo `raw` (base64url) da API do Gmail para os bytes
    do e-mail MIME completo."""
    padded = raw_base64url + "=" * (-len(raw_base64url) % 4)
    return base64.urlsafe_b64decode(padded)


def extract_pdf_attachment(raw_email_bytes: bytes) -> bytes:
    """Localiza e devolve os bytes do primeiro anexo PDF num e-mail MIME."""
    msg: Message = email.message_from_bytes(raw_email_bytes)
    for part in msg.walk():
        if part.get_content_type() == "application/pdf":
            payload = part.get_payload(decode=True)
            if payload:
                return payload
    raise ValueError("nenhum anexo PDF encontrado no e-mail")


def _parse_operacao_line(line: str) -> dict | None:
    m = _OPERACAO_RE.match(line.strip())
    if not m:
        return None
    cv, produto, qty, preco = m.groups()
    produto = produto.strip()
    ticker = TICKER_MAP.get(produto)
    if ticker is None:
        raise ProdutoNaoMapeado(produto)
    return {
        "ticker": ticker,
        "action": "compra" if cv == "C" else "venda",
        "qty": int(qty),
        "price": float(preco.replace(".", "").replace(",", ".")),
    }


def parse_nota_text(page_text: str) -> list[dict]:
    """Extrai as operações de uma página de nota já convertida em texto.
    Cada operação ganha a data da própria página ("Data pregão").
    Levanta ProdutoNaoMapeado se algum produto da nota não está em
    TICKER_MAP — o chamador deve tratar isso como "não commitar nada
    desta nota" (ver spec 003, risco de dado errado > dado faltando)."""
    date_match = _DATA_PREGAO_RE.search(page_text)
    if not date_match:
        return []
    dd, mm, yyyy = date_match.groups()
    date_iso = f"{yyyy}-{mm}-{dd}"

    operacoes = []
    for line in page_text.splitlines():
        op = _parse_operacao_line(line)
        if op is not None:
            op["date"] = date_iso
            operacoes.append(op)
    return operacoes


def decrypt_pdf(pdf_bytes: bytes, password: str) -> bytes:
    """Remove a proteção por senha do PDF, devolvendo os bytes decriptados."""
    import pikepdf

    with pikepdf.open(io.BytesIO(pdf_bytes), password=password) as pdf:
        out = io.BytesIO()
        pdf.save(out)
        return out.getvalue()


def parse_nota_pdf(pdf_bytes: bytes, password: str) -> list[dict]:
    """Decripta o PDF da nota e extrai todas as operações de todas as
    páginas. Cada item devolvido tem: date, ticker, action, qty, price."""
    import pdfplumber

    decrypted = decrypt_pdf(pdf_bytes, password)
    operacoes = []
    with pdfplumber.open(io.BytesIO(decrypted)) as doc:
        for page in doc.pages:
            text = page.extract_text() or ""
            operacoes.extend(parse_nota_text(text))
    return operacoes


def linhas_nao_reconhecidas_do_texto(page_text: str) -> list[str]:
    """Diagnóstico para quando uma página não rendeu nenhuma operação
    reconhecida: devolve as linhas que parecem ser uma operação (contêm
    "BOVESPA", o prefixo de toda linha de operação nas notas da Rico) mas
    não bateram com `_OPERACAO_RE` — ajuda a identificar rapidamente uma
    mudança de layout na nota sem precisar despejar o texto inteiro do
    PDF (que pode conter linhas irrelevantes) em log."""
    linhas = []
    for line in page_text.splitlines():
        if "BOVESPA" not in line:
            continue
        try:
            reconhecida = _parse_operacao_line(line) is not None
        except ProdutoNaoMapeado:
            reconhecida = True  # regex bateu, só o produto que não está mapeado
        if not reconhecida:
            linhas.append(line.strip())
    return linhas


def linhas_nao_reconhecidas(pdf_bytes: bytes, password: str) -> list[str]:
    """Mesma coisa que `linhas_nao_reconhecidas_do_texto`, mas a partir do
    PDF da nota (decripta e extrai o texto de todas as páginas)."""
    import pdfplumber

    decrypted = decrypt_pdf(pdf_bytes, password)
    linhas = []
    with pdfplumber.open(io.BytesIO(decrypted)) as doc:
        for page in doc.pages:
            text = page.extract_text() or ""
            linhas.extend(linhas_nao_reconhecidas_do_texto(text))
    return linhas


def transaction_csv_line(op: dict) -> str:
    return f"{op['date']},{op['ticker']},{op['action']},{op['qty']},{op['price']:.2f}"
