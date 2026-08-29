import base64
import sys
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from monitor.notas_rico import (
    ProdutoNaoMapeado,
    decode_raw_email,
    decrypt_pdf,
    extract_pdf_attachment,
    linhas_nao_reconhecidas_do_texto,
    parse_nota_text,
    transaction_csv_line,
)


def _build_raw_email(pdf_bytes: bytes) -> str:
    msg = MIMEMultipart()
    msg.attach(MIMEText("Nota de Negociação disponível.", "plain"))
    pdf_part = MIMEApplication(pdf_bytes, _subtype="pdf")
    pdf_part.add_header("Content-Disposition", "attachment", filename="nota.pdf")
    msg.attach(pdf_part)
    raw_bytes = msg.as_bytes()
    return base64.urlsafe_b64encode(raw_bytes).decode("ascii").rstrip("=")


def test_decode_raw_email_e_extract_pdf_attachment_roundtrip():
    pdf_bytes = b"%PDF-1.4 conteudo fake de teste"
    raw_b64url = _build_raw_email(pdf_bytes)

    decoded = decode_raw_email(raw_b64url)
    extracted = extract_pdf_attachment(decoded)

    assert extracted == pdf_bytes


def test_parse_nota_text_extrai_operacoes_e_mapeia_tickers():
    texto = """Negociações
Negócios realizados
Q Negociação C/V Tipo mercado Prazo Especificação do título Obs. (*) Quantidade Preço / Ajuste Valor Operação / Ajuste D/C
1-BOVESPA C VISTA INVESTOVWRA CI @ 12 115,55 1.386,60 D
1-BOVESPA C VISTA IT NOW IDIV CI @ 7 120,44 843,08 D
1-BOVESPA C VISTA TREND OURO CI @ 15 23,76 356,40 D
NOTA DE NEGOCIAÇÃO
Nr. nota
142444160
Folha
1
Data pregão
18/08/2026
"""
    operacoes = parse_nota_text(texto)

    assert operacoes == [
        {"ticker": "VWRA11", "action": "compra", "qty": 12, "price": 115.55, "date": "2026-08-18"},
        {"ticker": "DIVO11", "action": "compra", "qty": 7, "price": 120.44, "date": "2026-08-18"},
        {"ticker": "GOLD11", "action": "compra", "qty": 15, "price": 23.76, "date": "2026-08-18"},
    ]


def test_parse_nota_text_mapeia_venda():
    texto = """1-BOVESPA V VISTA INVESTOVWRA CI @ 3 120,00 360,00 D
Data pregão
01/09/2026
"""
    operacoes = parse_nota_text(texto)
    assert operacoes == [{"ticker": "VWRA11", "action": "venda", "qty": 3, "price": 120.00, "date": "2026-09-01"}]


def test_parse_nota_text_sem_data_pregao_devolve_lista_vazia():
    texto = "1-BOVESPA C VISTA INVESTOVWRA CI @ 12 115,55 1.386,60 D"
    assert parse_nota_text(texto) == []


def test_parse_nota_text_produto_desconhecido_levanta_erro_sem_adivinhar():
    texto = """1-BOVESPA C VISTA PRODUTO NOVO XYZ CI @ 1 10,00 10,00 D
Data pregão
01/09/2026
"""
    with pytest.raises(ProdutoNaoMapeado):
        parse_nota_text(texto)


def test_decrypt_pdf_remove_a_senha():
    pikepdf = pytest.importorskip("pikepdf")
    import io

    pdf = pikepdf.Pdf.new()
    pdf.add_blank_page(page_size=(200, 200))
    buf = io.BytesIO()
    pdf.save(buf, encryption=pikepdf.Encryption(owner="dono", user="796"))
    encrypted_bytes = buf.getvalue()

    decrypted_bytes = decrypt_pdf(encrypted_bytes, "796")

    with pikepdf.open(io.BytesIO(decrypted_bytes)) as reopened:
        assert len(reopened.pages) == 1


def test_linhas_nao_reconhecidas_do_texto_ignora_linha_que_bateu():
    texto = "1-BOVESPA C VISTA INVESTOVWRA CI @ 12 115,55 1.386,60 D"
    assert linhas_nao_reconhecidas_do_texto(texto) == []


def test_linhas_nao_reconhecidas_do_texto_ignora_produto_nao_mapeado():
    # Regex bateu (é uma operação de verdade), só o produto que não está
    # no TICKER_MAP — isso já é reportado como ProdutoNaoMapeado em outro
    # lugar, não deve aparecer como "linha não reconhecida" (diagnóstico
    # de mudança de layout, não de produto novo).
    texto = "1-BOVESPA C VISTA PRODUTO NOVO XYZ CI @ 1 10,00 10,00 D"
    assert linhas_nao_reconhecidas_do_texto(texto) == []


def test_linhas_nao_reconhecidas_do_texto_reporta_linha_fora_do_formato_esperado():
    texto = "Algo mudou no layout da Rico e a linha BOVESPA não bate mais com a regex"
    assert linhas_nao_reconhecidas_do_texto(texto) == [texto]


def test_linhas_nao_reconhecidas_do_texto_ignora_linhas_sem_bovespa():
    assert linhas_nao_reconhecidas_do_texto("Nota de Negociação\nData pregão\n01/09/2026") == []


def test_transaction_csv_line_formata_preco_com_duas_casas():
    op = {"date": "2026-08-18", "ticker": "B5P211", "action": "compra", "qty": 11, "price": 110.3}
    assert transaction_csv_line(op) == "2026-08-18,B5P211,compra,11,110.30"
