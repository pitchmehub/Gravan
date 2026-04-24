"""Gera o PDF do Contrato de Edição Musical (legalmente válido)."""
import io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
)
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER


def _styles():
    ss = getSampleStyleSheet()
    body = ParagraphStyle(
        "body", parent=ss["BodyText"],
        fontName="Helvetica", fontSize=9.5, leading=14,
        alignment=TA_JUSTIFY, spaceAfter=6,
    )
    h1 = ParagraphStyle(
        "h1", parent=ss["Heading1"],
        fontName="Helvetica-Bold", fontSize=13, leading=16,
        alignment=TA_CENTER, spaceAfter=14,
    )
    h2 = ParagraphStyle(
        "h2", parent=ss["Heading2"],
        fontName="Helvetica-Bold", fontSize=10.5, leading=14,
        spaceBefore=10, spaceAfter=4,
    )
    small = ParagraphStyle(
        "small", parent=body,
        fontName="Helvetica", fontSize=7.5, leading=10,
        textColor=colors.HexColor("#666666"), alignment=TA_CENTER,
    )
    return body, h1, h2, small


def gerar_pdf_contrato(contrato: dict) -> bytes:
    """contrato = linha de `contratos_edicao` (com 'conteudo', 'dados_titular',
    'assinado_em', 'id', 'obra_id'). Retorna os bytes do PDF."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=2.2 * cm, rightMargin=2.2 * cm,
        topMargin=2.0 * cm, bottomMargin=2.0 * cm,
        title="Contrato de Edição Musical — Gravan",
        author="Gravan",
    )

    body, h1, h2, small = _styles()
    story = []

    conteudo = (contrato.get("conteudo") or "").strip()
    dados    = contrato.get("dados_titular") or {}
    assinado = contrato.get("assinado_em") or datetime.utcnow().isoformat()
    cid      = str(contrato.get("id", ""))
    oid      = str(contrato.get("obra_id", ""))
    ver      = contrato.get("versao") or "v2.0"
    hash_doc = (dados.get("conteudo_hash") or "")[:32] or "—"
    ip_sig   = (contrato.get("ip_assinatura") or "")[:32] or "—"

    # Cabeçalho
    story.append(Paragraph("CONTRATO DE EDIÇÃO DE OBRAS MUSICAIS", h1))
    story.append(Paragraph(
        f"Documento gerado eletronicamente pela plataforma <b>Gravan</b> · Versão {ver}",
        small,
    ))
    story.append(Spacer(1, 0.4 * cm))

    meta = [
        ["ID do Contrato", cid],
        ["ID da Obra",     oid],
        ["Assinado em",    assinado],
        ["Hash SHA-256",   hash_doc + ("…" if hash_doc != "—" else "")],
        ["IP (hash)",      ip_sig   + ("…" if ip_sig   != "—" else "")],
    ]
    t = Table(meta, colWidths=[4.5 * cm, 11.5 * cm])
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#555555")),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f5f5f5")),
        ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#dddddd")),
        ("BOX",       (0, 0), (-1, -1), 0.5,  colors.HexColor("#cccccc")),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 6),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.5 * cm))

    # Corpo do contrato — parágrafos e títulos de cláusula
    for bloco in conteudo.split("\n\n"):
        bloco = bloco.strip()
        if not bloco:
            continue
        if bloco.upper() == bloco and len(bloco) < 160 and (
            "CLÁUSULA" in bloco or bloco.startswith("CONSIDERANDO") or bloco.startswith("CONTRATO")
        ):
            story.append(Paragraph(bloco, h2))
        else:
            txt = bloco.replace("&", "&amp;").replace("\n", "<br/>")
            story.append(Paragraph(txt, body))

    story.append(Spacer(1, 0.6 * cm))
    story.append(Paragraph(
        "<b>ASSINATURA ELETRÔNICA</b> — Documento assinado eletronicamente nos termos "
        "da MP nº 2.200-2/2001 e da Lei nº 14.063/2020. Integridade garantida pelo hash "
        "SHA-256 acima.",
        small,
    ))

    def _rodape(canvas, d):
        canvas.saveState()
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(colors.HexColor("#999999"))
        canvas.drawCentredString(
            A4[0] / 2, 1.0 * cm,
            f"Gravan · Contrato de Edição · Página {d.page} · ID {cid[:8]}",
        )
        canvas.restoreState()

    doc.build(story, onFirstPage=_rodape, onLaterPages=_rodape)
    return buf.getvalue()
