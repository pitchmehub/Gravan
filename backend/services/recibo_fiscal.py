"""
Recibo Fiscal Mensal de Rendimentos — GRAVAN.

Gera, para um perfil (compositor ou editora) e um período (ano/mês), o
recibo dos valores creditados pela plataforma, derivados da tabela
canônica `pagamentos_compositores` (1 linha por crédito de wallet).

Funções públicas:
    - meses_com_renda(perfil_id, limite_meses=12)
    - gerar_dados_recibo(perfil_id, ano, mes)
    - gerar_pdf_recibo(dados)

O recibo é informativo. A retenção tributária e a emissão de NFS-e são
de responsabilidade do beneficiário; o documento apenas demonstra os
valores creditados na plataforma no período.
"""
from __future__ import annotations

import io
from calendar import monthrange
from datetime import datetime, date
from decimal import Decimal

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

from db.supabase_client import get_supabase
from services.finance import EDITORA_RATE, PLATFORM_RATE
from utils.crypto import decrypt_pii


MES_PT = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
    5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
    9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro",
}


# ─────────────────────────── helpers ─────────────────────────────
def _brl(cents: int | None) -> str:
    cents = int(cents or 0)
    sign = "-" if cents < 0 else ""
    cents = abs(cents)
    reais, centavos = divmod(cents, 100)
    s = f"{reais:,}".replace(",", ".")
    return f"{sign}R$ {s},{centavos:02d}"


def _periodo(ano: int, mes: int) -> tuple[str, str]:
    if not (2000 <= ano <= 2100) or not (1 <= mes <= 12):
        raise ValueError("Período inválido (ano/mes).")
    ini = date(ano, mes, 1).isoformat()
    last_day = monthrange(ano, mes)[1]
    fim = f"{ano:04d}-{mes:02d}-{last_day:02d}T23:59:59.999999Z"
    return ini, fim


def _nome_perfil(p: dict) -> str:
    if not p:
        return "—"
    return (
        p.get("razao_social")
        or p.get("nome_fantasia")
        or p.get("nome_artistico")
        or p.get("nome_completo")
        or "—"
    )


def _doc_perfil(p: dict) -> str:
    """CNPJ se editora, senão usa cpf."""
    if not p:
        return "—"
    if p.get("role") == "publisher":
        return p.get("cnpj") or "—"
    return p.get("cpf_display") or p.get("cpf") or "—"


def _endereco(p: dict) -> str:
    if not p:
        return "—"
    parts = [
        p.get("endereco_rua"), p.get("endereco_numero"),
        p.get("endereco_bairro"), p.get("endereco_cidade"),
        p.get("endereco_uf"), p.get("endereco_cep"),
    ]
    return ", ".join([x for x in parts if x]) or "—"


# ───────────────────────── meses com renda ───────────────────────
def meses_com_renda(perfil_id: str, limite_meses: int = 12) -> list[dict]:
    """Lista os meses (até `limite_meses` recentes) em que o perfil
    recebeu créditos. Cada item: {ano, mes, label, total_cents}."""
    sb = get_supabase()
    rows = (
        sb.table("pagamentos_compositores")
          .select("valor_cents, created_at")
          .eq("perfil_id", perfil_id)
          .order("created_at", desc=True)
          .limit(2000)
          .execute()
    ).data or []

    bucket: dict[tuple[int, int], int] = {}
    for r in rows:
        try:
            dt = datetime.fromisoformat((r["created_at"] or "").replace("Z", "+00:00"))
        except Exception:
            continue
        chave = (dt.year, dt.month)
        bucket[chave] = bucket.get(chave, 0) + int(r.get("valor_cents") or 0)

    itens = [
        {
            "ano": ano,
            "mes": mes,
            "label": f"{MES_PT[mes]}/{ano}",
            "total_cents": total,
        }
        for (ano, mes), total in bucket.items()
        if total > 0
    ]
    itens.sort(key=lambda x: (x["ano"], x["mes"]), reverse=True)
    return itens[:limite_meses]


# ─────────────────────────── recibo ──────────────────────────────
def gerar_dados_recibo(perfil_id: str, ano: int, mes: int) -> dict:
    """
    Agrega o recibo fiscal mensal do perfil. Retorna dict com:
      - beneficiario:  {id, nome, documento, endereco, tipo}
      - periodo:       {ano, mes, label, inicio, fim}
      - linhas[]:      {data, obra_id, obra_nome, transacao_id,
                         pagador_nome, valor_total_cents, share_pct,
                         valor_creditado_cents, papel}
      - totais:        {bruto_creditado_cents, qtd_transacoes,
                         platform_fee_cents_informativo,
                         exploracao_fee_cents_informativo,
                         ytd_cents}
      - disclaimer
    """
    sb = get_supabase()
    inicio, fim = _periodo(ano, mes)

    perfil = (
        sb.table("perfis")
          .select(
              "id, role, nome_completo, nome_artistico, razao_social, "
              "nome_fantasia, cnpj, cpf, endereco_rua, "
              "endereco_numero, endereco_bairro, endereco_cidade, "
              "endereco_uf, endereco_cep"
          )
          .eq("id", perfil_id)
          .single()
          .execute()
    ).data
    if not perfil:
        raise ValueError("Perfil não encontrado.")

    # descriptografa o CPF para exibição no recibo
    if perfil.get("cpf"):
        try:
            perfil["cpf_display"] = decrypt_pii(perfil["cpf"])
        except Exception:
            perfil["cpf_display"] = perfil["cpf"]

    pagamentos = (
        sb.table("pagamentos_compositores")
          .select("id, transacao_id, valor_cents, share_pct, created_at")
          .eq("perfil_id", perfil_id)
          .gte("created_at", inicio)
          .lte("created_at", fim)
          .order("created_at", desc=False)
          .execute()
    ).data or []

    tx_ids = list({p["transacao_id"] for p in pagamentos if p.get("transacao_id")})
    tx_map: dict = {}
    obra_map: dict = {}
    if tx_ids:
        try:
            tx = (
                sb.table("transacoes")
                  .select(
                      "id, valor_cents, status, created_at, obra_id, "
                      "comprador_id, obras(id, nome, titular_id, "
                      "publisher_id, editora_terceira_id)"
                  )
                  .in_("id", tx_ids)
                  .execute()
            ).data or []
            for t in tx:
                tx_map[t["id"]] = t
                ob = t.get("obras")
                if isinstance(ob, dict) and ob.get("id"):
                    obra_map[ob["id"]] = ob
                elif isinstance(ob, list) and ob:
                    obra_map[ob[0]["id"]] = ob[0]
        except Exception:
            tx = (
                sb.table("transacoes")
                  .select("id, valor_cents, status, created_at, obra_id, comprador_id")
                  .in_("id", tx_ids)
                  .execute()
            ).data or []
            tx_map = {t["id"]: t for t in tx}
            obra_ids = [t.get("obra_id") for t in tx if t.get("obra_id")]
            if obra_ids:
                obs = (
                    sb.table("obras")
                      .select("id, nome, titular_id, publisher_id, editora_terceira_id")
                      .in_("id", obra_ids)
                      .execute()
                ).data or []
                obra_map = {o["id"]: o for o in obs}

    pagadores_ids = list({
        t.get("comprador_id") for t in tx_map.values() if t.get("comprador_id")
    })
    pagador_map: dict = {}
    if pagadores_ids:
        try:
            ps = (
                sb.table("perfis")
                  .select("id, nome_completo, nome_artistico, razao_social, nome_fantasia")
                  .in_("id", pagadores_ids)
                  .execute()
            ).data or []
            pagador_map = {p["id"]: p for p in ps}
        except Exception:
            pagador_map = {}

    eh_publisher = (perfil.get("role") == "publisher")
    linhas = []
    bruto = 0
    plataforma_inf = 0
    exploracao_inf = 0
    for p in pagamentos:
        t = tx_map.get(p.get("transacao_id")) or {}
        oid = t.get("obra_id")
        obra = obra_map.get(oid) or {}
        pagador = pagador_map.get(t.get("comprador_id")) or {}

        valor_total = int(t.get("valor_cents") or 0)
        valor_cred = int(p.get("valor_cents") or 0)
        share = p.get("share_pct")

        # Fees informativos calculados sobre o valor bruto da transação:
        # 25% plataforma, 5% exploração comercial (cláusula 5/6.3 GRAVAN)
        plat_inf = int(Decimal(valor_total) * PLATFORM_RATE)
        expl_inf = int(Decimal(valor_total) * Decimal("0.05"))

        plataforma_inf += plat_inf
        exploracao_inf += expl_inf
        bruto += valor_cred

        # Papel do beneficiário nessa linha
        if eh_publisher:
            papel = "Editora (10% sobre exploração)"
        elif obra.get("titular_id") == perfil_id:
            papel = "Compositor titular"
        else:
            papel = "Coautor"

        linhas.append({
            "data": p.get("created_at"),
            "obra_id": oid,
            "obra_nome": obra.get("nome") or "—",
            "transacao_id": p.get("transacao_id"),
            "pagador_nome": _nome_perfil(pagador),
            "valor_total_cents": valor_total,
            "share_pct": float(share) if share is not None else None,
            "valor_creditado_cents": valor_cred,
            "papel": papel,
        })

    # YTD acumulado
    ytd_inicio = date(ano, 1, 1).isoformat()
    ytd_rows = (
        sb.table("pagamentos_compositores")
          .select("valor_cents, created_at")
          .eq("perfil_id", perfil_id)
          .gte("created_at", ytd_inicio)
          .lte("created_at", fim)
          .execute()
    ).data or []
    ytd_cents = sum(int(r.get("valor_cents") or 0) for r in ytd_rows)

    return {
        "beneficiario": {
            "id": perfil["id"],
            "nome": _nome_perfil(perfil),
            "documento": _doc_perfil(perfil),
            "endereco": _endereco(perfil),
            "tipo": "Editora (PJ)" if eh_publisher else "Compositor (PF)",
            "role": perfil.get("role"),
        },
        "periodo": {
            "ano": ano,
            "mes": mes,
            "label": f"{MES_PT[mes]}/{ano}",
            "inicio": inicio,
            "fim": fim,
        },
        "linhas": linhas,
        "totais": {
            "bruto_creditado_cents": bruto,
            "qtd_transacoes": len({l["transacao_id"] for l in linhas if l.get("transacao_id")}),
            "platform_fee_cents_informativo": plataforma_inf,
            "exploracao_fee_cents_informativo": exploracao_inf,
            "ytd_cents": ytd_cents,
            "platform_rate_pct": float(PLATFORM_RATE * 100),
            "editora_rate_pct": float(EDITORA_RATE * 100),
        },
        "disclaimer": (
            "Documento informativo emitido pela plataforma GRAVAN. Os "
            "valores apresentados correspondem aos créditos realizados "
            "na carteira do beneficiário no período. A apuração e o "
            "recolhimento de tributos (IRRF, ISS, INSS, etc.) e a "
            "emissão de nota fiscal de serviço (NFS-e), quando "
            "aplicáveis, são de responsabilidade exclusiva do "
            "beneficiário, observada a sua natureza jurídica. Os fees "
            "destacados (25% plataforma e 5% exploração comercial) são "
            "informativos e já estão deduzidos do valor creditado."
        ),
        "emitido_em": datetime.utcnow().isoformat() + "Z",
    }


# ─────────────────────────── PDF ──────────────────────────────────
def _styles():
    ss = getSampleStyleSheet()
    body = ParagraphStyle(
        "body", parent=ss["BodyText"],
        fontName="Helvetica", fontSize=9.5, leading=13,
        alignment=TA_JUSTIFY, spaceAfter=4,
    )
    h1 = ParagraphStyle(
        "h1", parent=ss["Heading1"],
        fontName="Helvetica-Bold", fontSize=14, leading=18,
        alignment=TA_CENTER, spaceAfter=10,
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


def gerar_pdf_recibo(dados: dict) -> bytes:
    """Gera o PDF do recibo a partir do dict de `gerar_dados_recibo`."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=2.0 * cm, rightMargin=2.0 * cm,
        topMargin=1.8 * cm, bottomMargin=1.8 * cm,
        title=f"Recibo de Rendimentos — {dados['periodo']['label']}",
        author="Gravan",
    )
    body, h1, h2, small = _styles()
    story = []

    benef = dados["beneficiario"]
    per = dados["periodo"]
    tot = dados["totais"]

    story.append(Paragraph("RECIBO DE RENDIMENTOS — PLATAFORMA GRAVAN", h1))
    story.append(Paragraph(
        f"Período de referência: <b>{per['label']}</b> · "
        f"Emitido em {dados.get('emitido_em','')[:10]}",
        small,
    ))
    story.append(Spacer(1, 0.4 * cm))

    # Cabeçalho beneficiário
    cab = [
        ["Beneficiário", benef["nome"]],
        ["Tipo", benef["tipo"]],
        ["Documento", benef["documento"]],
        ["Endereço", benef["endereco"]],
        ["ID na plataforma", benef["id"]],
    ]
    t = Table(cab, colWidths=[4.0 * cm, 12.0 * cm])
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#555555")),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f5f5f5")),
        ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#dddddd")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.4 * cm))

    # Tabela detalhe
    story.append(Paragraph("DETALHAMENTO DOS CRÉDITOS NO PERÍODO", h2))
    if not dados["linhas"]:
        story.append(Paragraph(
            "Nenhum crédito registrado no período.", body,
        ))
    else:
        cab_det = [
            "Data", "Obra", "Pagador", "Papel",
            "Valor bruto", "Share %", "Creditado",
        ]
        rows = [cab_det]
        for l in dados["linhas"]:
            data_fmt = (l.get("data") or "")[:10]
            share = l.get("share_pct")
            share_fmt = f"{share:.2f}%" if share is not None else "—"
            rows.append([
                data_fmt,
                Paragraph(l.get("obra_nome") or "—", body),
                Paragraph(l.get("pagador_nome") or "—", body),
                Paragraph(l.get("papel") or "—", body),
                _brl(l.get("valor_total_cents")),
                share_fmt,
                _brl(l.get("valor_creditado_cents")),
            ])
        det = Table(
            rows,
            colWidths=[1.9 * cm, 3.6 * cm, 3.0 * cm, 2.6 * cm,
                       2.1 * cm, 1.4 * cm, 2.4 * cm],
            repeatRows=1,
        )
        det.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 7.5),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eeeeee")),
            ("ALIGN", (4, 1), (-1, -1), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#dddddd")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(det)
    story.append(Spacer(1, 0.4 * cm))

    # Totais
    story.append(Paragraph("TOTAIS DO PERÍODO", h2))
    totais_rows = [
        ["Total bruto creditado no mês", _brl(tot["bruto_creditado_cents"])],
        ["Quantidade de transações", str(tot["qtd_transacoes"])],
        [
            f"Fee plataforma GRAVAN (informativo, {tot['platform_rate_pct']:.0f}%)",
            _brl(tot["platform_fee_cents_informativo"]),
        ],
        [
            "Fee exploração comercial (informativo, 5%)",
            _brl(tot["exploracao_fee_cents_informativo"]),
        ],
        [
            f"Acumulado no ano ({per['ano']}, até {per['label']})",
            _brl(tot["ytd_cents"]),
        ],
    ]
    tt = Table(totais_rows, colWidths=[11.0 * cm, 5.0 * cm])
    tt.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("FONTNAME", (0, 0), (0, 0), "Helvetica-Bold"),
        ("FONTNAME", (1, 0), (1, 0), "Helvetica-Bold"),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f5f5f5")),
        ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#dddddd")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(tt)
    story.append(Spacer(1, 0.5 * cm))

    # Observações fiscais
    story.append(Paragraph("OBSERVAÇÕES FISCAIS", h2))
    story.append(Paragraph(dados.get("disclaimer", ""), body))

    def _rodape(canvas, d):
        canvas.saveState()
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(colors.HexColor("#999999"))
        canvas.drawCentredString(
            A4[0] / 2, 1.0 * cm,
            f"GRAVAN · Recibo de Rendimentos · {per['label']} · "
            f"Página {d.page} · Beneficiário {benef['id'][:8]}",
        )
        canvas.restoreState()

    doc.build(story, onFirstPage=_rodape, onLaterPages=_rodape)
    return buf.getvalue()
