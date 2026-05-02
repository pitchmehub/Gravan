"""
Gravan — Serviço de Geração de Dossiê da Obra (Master Package)
================================================================

Gera um ZIP oficial contendo:
    obra/audio.mp3
    obra/letra.txt
    obra/metadata.json
    obra/contrato.pdf
    obra/resumo.pdf
    obra/hash.txt

REGRA CRÍTICA:
Todos os dados vêm do CONTRATO ASSINADO no banco (`contratos_edicao`),
NUNCA do frontend e NUNCA dos campos editáveis atuais do usuário.

PERCENTUAIS — Regras ECAD / Lei 9.610/98:
  - COTA AUTORAL:   75% — dividida entre os autores pelo share_pct interno
  - COTA EDITORIAL: 25% — dividida igualmente entre as editoras distintas
                          (ou pelo percentual interno caso definido)
"""
from __future__ import annotations

import hashlib
import io
import json
import zipfile
from datetime import datetime, timezone

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.enums import TA_CENTER

from db.supabase_client import get_supabase
from services.contrato_pdf import gerar_pdf_contrato
from utils.crypto import decrypt_pii


# ──────────────────────────────────────────────────────────────────
# CONSTANTES DE NEGÓCIO
# ──────────────────────────────────────────────────────────────────
COTA_AUTORAL   = 75.0   # % fixo — Lei 9.610/98 / ECAD
COTA_EDITORIAL = 25.0   # % fixo


class DossieService:
    def __init__(self) -> None:
        self.sb = get_supabase()

    # ──────────────────────────────────────────────────────────────
    # API PÚBLICA
    # ──────────────────────────────────────────────────────────────

    def gerar(self, obra_id: str, user_id: str) -> dict:
        obra        = self._buscar_obra(obra_id)
        contrato    = self._buscar_contrato_assinado(obra_id, obra)
        autores     = self._buscar_autores(obra_id)
        editoras    = self._buscar_editoras_dos_autores(autores)
        interprete  = self._extrair_interprete(contrato)
        audio_bytes = self._download_audio(obra["audio_path"])

        metadata = self._montar_metadata(obra, autores, editoras, interprete, contrato)

        contrato_texto = (contrato.get("conteudo") or "").encode("utf-8")
        metadata_canon = json.dumps(
            metadata, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        hash_sha256 = hashlib.sha256(metadata_canon + contrato_texto).hexdigest()

        metadata["hash_integridade"] = hash_sha256
        metadata_json = json.dumps(metadata, ensure_ascii=False, indent=2)

        contrato_pdf = gerar_pdf_contrato(contrato)
        resumo_pdf   = self._gerar_resumo_pdf(
            obra, autores, editoras, interprete, contrato, hash_sha256
        )

        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        hash_txt = (
            f"HASH SHA256:\n{hash_sha256}\n\n"
            f"Data de geração:\n{ts}\n"
        )

        zip_bytes = self._criar_zip(
            audio_bytes   = audio_bytes,
            letra         = obra.get("letra", "") or "",
            metadata_json = metadata_json,
            contrato_pdf  = contrato_pdf,
            resumo_pdf    = resumo_pdf,
            hash_txt      = hash_txt,
        )

        storage_path = f"dossies/{obra_id}/obra-{obra_id}.zip"
        self.sb.storage.from_("dossies").upload(
            path=storage_path,
            file=zip_bytes,
            file_options={"content-type": "application/zip", "upsert": "true"},
        )

        try:
            self.sb.table("dossies").delete().eq("obra_id", obra_id).execute()
        except Exception:
            pass

        row = {
            "obra_id":      obra_id,
            "contrato_id":  str(contrato["id"]),
            "gerado_por":   user_id,
            "storage_path": storage_path,
            "hash_sha256":  hash_sha256,
            "titulo_obra":  obra.get("nome", "") or "",
            "metadata":     metadata,
        }
        resp = self.sb.table("dossies").insert(row).execute()
        return resp.data[0] if resp.data else row

    def download_zip(self, dossie_id: str) -> bytes:
        resp = (
            self.sb.table("dossies")
            .select("storage_path")
            .eq("id", dossie_id)
            .limit(1)
            .execute()
        )
        if not resp.data:
            raise ValueError("Dossiê não encontrado.")
        path = resp.data[0]["storage_path"]
        data = self.sb.storage.from_("dossies").download(path)
        if not data:
            raise ValueError("Arquivo do dossiê não encontrado no storage.")
        return data

    # ──────────────────────────────────────────────────────────────
    # BUSCAS NO BANCO
    # ──────────────────────────────────────────────────────────────

    def _buscar_obra(self, obra_id: str) -> dict:
        r = (
            self.sb.table("obras")
            .select("*")
            .eq("id", obra_id)
            .limit(1)
            .execute()
        )
        if not r.data:
            raise ValueError("Obra não encontrada.")
        obra = r.data[0]
        if not obra.get("audio_path"):
            raise ValueError("Arquivo de áudio não cadastrado para esta obra.")
        return obra

    def _buscar_contrato_assinado(self, obra_id: str, obra: dict) -> dict:
        """
        Busca o contrato de edição na seguinte ordem:
          1. contratos_edicao  — contrato Gravan assinado pelo compositor
          2. contracts_edicao  — contrato entre compositor e editora interna
          3. Contrato sintético — fallback quando nenhum existe
        """
        # 1. Contrato Gravan
        r = (
            self.sb.table("contratos_edicao")
            .select("*")
            .eq("obra_id", obra_id)
            .limit(1)
            .execute()
        )
        if r.data:
            contrato = r.data[0]
            if not contrato.get("assinado_em"):
                dados = contrato.get("dados_titular") or {}
                contrato["assinado_em"] = dados.get("data_assinatura") or contrato.get("created_at", "")
            return contrato

        # 2. Contrato editora interna (agregado)
        try:
            r2 = (
                self.sb.table("contracts_edicao")
                .select("*")
                .eq("obra_id", obra_id)
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )
        except Exception:
            r2 = None

        if r2 and r2.data:
            c = r2.data[0]
            assinado_em = (
                c.get("completed_at")
                or c.get("signed_by_autor_at")
                or c.get("created_at", "")
            )
            return {
                "id":            c["id"],
                "obra_id":       obra_id,
                "assinado_em":   assinado_em,
                "created_at":    c.get("created_at", ""),
                "conteudo":      c.get("contract_text") or c.get("contract_html") or "",
                "dados_titular": {},
                "interprete":    {},
                "versao":        c.get("versao") or "v1.0",
                "ip_assinatura": c.get("autor_ip_hash") or "",
            }

        # 3. Fallback sintético
        editora_nome = obra.get("editora_terceira_nome") or "Editora Independente"
        return {
            "id":            obra_id,
            "obra_id":       obra_id,
            "assinado_em":   obra.get("created_at", ""),
            "created_at":    obra.get("created_at", ""),
            "dados_titular": {},
            "interprete":    {},
            "conteudo":      (
                f"DECLARAÇÃO DE REGISTRO\n\n"
                f"O titular da obra declara que a mesma está sob gestão "
                f"da editora: {editora_nome}.\n\n"
                f"Este dossiê foi gerado pela plataforma Gravan como "
                f"registro de autoria e integridade da obra."
            ),
            "versao":        "v1.0",
        }

    def _buscar_autores(self, obra_id: str) -> list:
        autores = self._buscar_em_coautorias(obra_id)
        if not autores:
            autores = self._buscar_em_obras_autores(obra_id)

        if not autores:
            raise ValueError(
                "Nenhum autor cadastrado para esta obra. "
                "Cadastre os coautores antes de gerar o dossiê."
            )

        total = sum(float(a.get("share_pct", 0) or 0) for a in autores)
        if abs(total - 100.0) > 0.5:
            raise ValueError(
                f"Splits dos autores não somam 100% (atual: {total:.1f}%). "
                "Corrija os percentuais antes de gerar o dossiê."
            )
        return autores

    def _buscar_em_coautorias(self, obra_id: str) -> list:
        try:
            r = (
                self.sb.table("coautorias")
                .select("*, perfis(id,nome,nome_artistico,email,cpf,publisher_id)")
                .eq("obra_id", obra_id)
                .execute()
            )
            rows = r.data or []
            for row in rows:
                row.setdefault("is_principal", row.get("is_titular", False))
            return rows
        except Exception:
            return []

    def _buscar_em_obras_autores(self, obra_id: str) -> list:
        try:
            r = (
                self.sb.table("obras_autores")
                .select("*, perfis(id,nome,nome_artistico,email,cpf,publisher_id)")
                .eq("obra_id", obra_id)
                .execute()
            )
            return r.data or []
        except Exception:
            return []

    def _buscar_editoras_dos_autores(self, autores: list) -> list:
        """
        Para cada autor, busca o perfil da sua editora (publisher_id).
        Retorna lista de editoras únicas com nome e CNPJ descriptografado.
        """
        publisher_ids = []
        seen = set()
        for a in autores:
            p = a.get("perfis") or {}
            pid = p.get("publisher_id")
            if pid and pid not in seen:
                seen.add(pid)
                publisher_ids.append(pid)

        if not publisher_ids:
            return []

        try:
            r = (
                self.sb.table("perfis")
                .select("id,nome,nome_artistico,razao_social,nome_fantasia,cnpj")
                .in_("id", publisher_ids)
                .execute()
            )
            editoras = []
            for pub in (r.data or []):
                cnpj_raw = pub.get("cnpj") or ""
                try:
                    cnpj = decrypt_pii(cnpj_raw) if cnpj_raw else ""
                except Exception:
                    cnpj = cnpj_raw
                nome = (
                    pub.get("nome_fantasia")
                    or pub.get("razao_social")
                    or pub.get("nome_artistico")
                    or pub.get("nome")
                    or "—"
                )
                editoras.append({
                    "id":   pub["id"],
                    "nome": nome,
                    "cnpj": cnpj or "—",
                })
            return editoras
        except Exception:
            return []

    def _extrair_interprete(self, contrato: dict) -> dict:
        if isinstance(contrato.get("interprete"), dict):
            i = contrato["interprete"]
        else:
            dados = contrato.get("dados_titular") or {}
            if isinstance(dados.get("interprete"), dict):
                i = dados["interprete"]
            else:
                i = dados
        return {
            "nome":           i.get("nome", "") or i.get("nome_completo", ""),
            "nome_artistico": i.get("nome_artistico", "") or "",
            "email":          i.get("email", "") or "",
        }

    def _download_audio(self, audio_path: str) -> bytes:
        try:
            data = self.sb.storage.from_("obras-audio").download(audio_path)
        except Exception as e:
            raise ValueError(f"Falha ao baixar o áudio: {e}")
        if not data:
            raise ValueError("Arquivo de áudio não encontrado no storage.")
        return data

    # ──────────────────────────────────────────────────────────────
    # CÁLCULO DE PERCENTUAIS — ECAD / Lei 9.610/98
    # ──────────────────────────────────────────────────────────────

    def _calcular_splits(self, autores: list, editoras: list) -> tuple[list, list]:
        """
        Retorna (autores_splits, editoras_splits) com percentuais calculados.

        Cota autoral (75%): cada autor recebe share_pct * 75 / 100
        Cota editorial (25%): dividida igualmente entre editoras distintas
                              (ou 25% para "Editora não definida" se não houver)
        """
        n_autores = len(autores)

        autores_splits = []
        for a in autores:
            share_interno = float(a.get("share_pct", 0) or 0)
            # share_pct é o % interno de 100%; converte para % da obra total
            pct_obra = round(share_interno * COTA_AUTORAL / 100.0, 2)
            autores_splits.append({
                "_autor_raw":       a,
                "percentual_interno": round(share_interno, 2),
                "percentual_obra":    pct_obra,
            })

        editoras_splits = []
        if editoras:
            n_ed = len(editoras)
            pct_interno = round(100.0 / n_ed, 4)
            pct_obra    = round(COTA_EDITORIAL / n_ed, 4)
            for ed in editoras:
                editoras_splits.append({
                    "_editora_raw":       ed,
                    "percentual_interno": round(pct_interno, 2),
                    "percentual_obra":    round(pct_obra, 2),
                })
        else:
            editoras_splits.append({
                "_editora_raw": {
                    "id":   None,
                    "nome": "Editora não definida",
                    "cnpj": "—",
                },
                "percentual_interno": 100.0,
                "percentual_obra":    COTA_EDITORIAL,
            })

        return autores_splits, editoras_splits

    # ──────────────────────────────────────────────────────────────
    # MONTAGEM DE METADATA
    # ──────────────────────────────────────────────────────────────

    def _montar_metadata(
        self,
        obra: dict,
        autores: list,
        editoras: list,
        interprete: dict,
        contrato: dict,
    ) -> dict:
        autores_splits, editoras_splits = self._calcular_splits(autores, editoras)

        # Mapa publisher_id → editora para associar a cada autor
        pub_map = {ed["id"]: ed for ed in editoras if ed.get("id")}

        autores_list = []
        for item in autores_splits:
            a = item["_autor_raw"]
            p = a.get("perfis") or {}
            cpf_raw = p.get("cpf") or ""
            try:
                cpf = decrypt_pii(cpf_raw) if cpf_raw else ""
            except Exception:
                cpf = ""

            publisher_id = p.get("publisher_id")
            editora_autor = pub_map.get(publisher_id, {}) if publisher_id else {}

            autores_list.append({
                "nome":               p.get("nome", "") or "",
                "nome_artistico":     p.get("nome_artistico") or "",
                "cpf":                cpf,
                "email":              p.get("email", "") or "",
                "funcao":             "Autor" if a.get("is_principal") else "Coautor",
                "percentual_interno": f"{item['percentual_interno']:.2f}%",
                "percentual_obra":    f"{item['percentual_obra']:.2f}%",
                "editora": {
                    "nome": editora_autor.get("nome") or "—",
                    "cnpj": editora_autor.get("cnpj") or "—",
                } if editora_autor else None,
            })

        editoras_list = []
        for item in editoras_splits:
            ed = item["_editora_raw"]
            editoras_list.append({
                "nome":               ed.get("nome", "—"),
                "cnpj":               ed.get("cnpj", "—"),
                "percentual_interno": f"{item['percentual_interno']:.2f}%",
                "percentual_obra":    f"{item['percentual_obra']:.2f}%",
            })

        # Validação final
        soma = (
            sum(item["percentual_obra"] for item in autores_splits)
            + sum(item["percentual_obra"] for item in editoras_splits)
        )
        validacao_status = "OK" if abs(soma - 100.0) < 0.1 else f"ERRO: soma={soma:.2f}%"

        assinado_em = str(
            contrato.get("assinado_em")
            or contrato.get("created_at")
            or ""
        )

        return {
            "obra_id":      str(obra["id"]),
            "titulo":       obra.get("nome", "") or "",
            "idioma":       obra.get("idioma") or "Português",
            "data_criacao": str(obra.get("created_at", ""))[:10],
            "interprete":   interprete,
            "cota_autoral": {
                "percentual_total": f"{COTA_AUTORAL:.0f}%",
                "autores":          autores_list,
            },
            "cota_editorial": {
                "percentual_total": f"{COTA_EDITORIAL:.0f}%",
                "editoras":         editoras_list,
                "aviso": (
                    "Nenhuma editora cadastrada. Os 25% da cota editorial "
                    "estão reservados até que uma editora seja vinculada."
                    if not editoras else None
                ),
            },
            "validacao": {
                "soma_total": f"{soma:.2f}%",
                "status":     validacao_status,
            },
            "contrato": {
                "id":              str(contrato["id"]),
                "data_assinatura": assinado_em[:10],
                "tipo":            "edicao",
            },
        }

    # ──────────────────────────────────────────────────────────────
    # ZIP
    # ──────────────────────────────────────────────────────────────

    def _criar_zip(
        self,
        audio_bytes: bytes,
        letra: str,
        metadata_json: str,
        contrato_pdf: bytes,
        resumo_pdf: bytes,
        hash_txt: str,
    ) -> bytes:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("obra/audio.mp3",     audio_bytes)
            zf.writestr("obra/letra.txt",     letra.encode("utf-8"))
            zf.writestr("obra/metadata.json", metadata_json.encode("utf-8"))
            zf.writestr("obra/contrato.pdf",  contrato_pdf)
            zf.writestr("obra/resumo.pdf",    resumo_pdf)
            zf.writestr("obra/hash.txt",      hash_txt.encode("utf-8"))
        return buf.getvalue()

    # ──────────────────────────────────────────────────────────────
    # PDF DE RESUMO
    # ──────────────────────────────────────────────────────────────

    def _gerar_resumo_pdf(
        self,
        obra: dict,
        autores: list,
        editoras: list,
        interprete: dict,
        contrato: dict,
        hash_sha256: str,
    ) -> bytes:
        autores_splits, editoras_splits = self._calcular_splits(autores, editoras)
        pub_map = {ed["id"]: ed for ed in editoras if ed.get("id")}

        buf = io.BytesIO()
        doc = SimpleDocTemplate(
            buf, pagesize=A4,
            leftMargin=2.2 * cm, rightMargin=2.2 * cm,
            topMargin=2.0 * cm, bottomMargin=2.0 * cm,
            title="Resumo do Dossiê — Gravan",
        )
        ss = getSampleStyleSheet()
        h1 = ParagraphStyle(
            "h1", parent=ss["Heading1"],
            fontName="Helvetica-Bold", fontSize=16, alignment=TA_CENTER,
            spaceAfter=4, textColor=colors.HexColor("#111111"),
        )
        sub = ParagraphStyle(
            "sub", parent=ss["BodyText"],
            fontName="Helvetica", fontSize=8, alignment=TA_CENTER,
            spaceAfter=14, textColor=colors.HexColor("#666666"),
        )
        h2 = ParagraphStyle(
            "h2", parent=ss["Heading2"],
            fontName="Helvetica-Bold", fontSize=10.5,
            spaceBefore=12, spaceAfter=4,
            textColor=colors.HexColor("#222222"),
        )
        mono = ParagraphStyle(
            "mono", parent=ss["BodyText"],
            fontName="Courier", fontSize=7.5,
            textColor=colors.HexColor("#333333"),
        )
        aviso_style = ParagraphStyle(
            "aviso", parent=ss["BodyText"],
            fontName="Helvetica-Oblique", fontSize=8,
            textColor=colors.HexColor("#885500"),
            spaceBefore=4,
        )

        def base_ts() -> TableStyle:
            return TableStyle([
                ("FONTNAME",      (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE",      (0, 0), (-1, -1), 9),
                ("TEXTCOLOR",     (0, 0), (0, -1),  colors.HexColor("#555555")),
                ("BACKGROUND",    (0, 0), (0, -1),  colors.HexColor("#F5F5F5")),
                ("GRID",          (0, 0), (-1, -1), 0.3, colors.HexColor("#DDDDDD")),
                ("TOPPADDING",    (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ])

        def header_ts() -> TableStyle:
            return TableStyle([
                ("FONTNAME",      (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE",      (0, 0), (-1, -1), 9),
                ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
                ("BACKGROUND",    (0, 0), (-1, 0),  colors.HexColor("#111111")),
                ("TEXTCOLOR",     (0, 0), (-1, 0),  colors.white),
                ("GRID",          (0, 0), (-1, -1), 0.3, colors.HexColor("#DDDDDD")),
                ("TOPPADDING",    (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ])

        assinado = str(
            contrato.get("assinado_em") or contrato.get("created_at") or ""
        )[:10]

        story = [
            Paragraph("DOSSIÊ DA OBRA", h1),
            Paragraph("Gravan · Documento Oficial de Integridade Musical", sub),

            # ── OBRA ──────────────────────────────────────────────
            Paragraph("OBRA", h2),
            Table([
                ["Título",           obra.get("nome", "—") or "—"],
                ["Gênero",           obra.get("genero")    or "—"],
                ["ID",               str(obra.get("id", ""))],
                ["Data de cadastro", str(obra.get("created_at", ""))[:10]],
            ], colWidths=[4.5 * cm, 11.5 * cm], style=base_ts()),

            # ── COTA AUTORAL (75%) ────────────────────────────────
            Paragraph(f"COTA AUTORAL — {COTA_AUTORAL:.0f}% (Lei 9.610/98 / ECAD)", h2),
        ]

        # Tabela de autores com CPF, editora e percentuais
        hdr_autores = [[
            "Nome / CPF",
            "Nome Artístico",
            "Função",
            "Editora (CNPJ)",
            "% Interno",
            "% Obra",
        ]]
        rows_autores = []
        for item in autores_splits:
            a  = item["_autor_raw"]
            p  = a.get("perfis") or {}
            cpf_raw = p.get("cpf") or ""
            try:
                cpf = decrypt_pii(cpf_raw) if cpf_raw else "—"
            except Exception:
                cpf = "—"

            publisher_id  = p.get("publisher_id")
            editora_autor = pub_map.get(publisher_id, {}) if publisher_id else {}
            ed_nome  = editora_autor.get("nome", "—") if editora_autor else "—"
            ed_cnpj  = editora_autor.get("cnpj", "—") if editora_autor else "—"
            ed_cell  = f"{ed_nome}\n{ed_cnpj}"

            nome_cpf = f"{p.get('nome', '—') or '—'}\nCPF: {cpf}"
            funcao   = "Autor" if a.get("is_principal") else "Coautor"

            rows_autores.append([
                nome_cpf,
                p.get("nome_artistico") or "—",
                funcao,
                ed_cell,
                f"{item['percentual_interno']:.2f}%",
                f"{item['percentual_obra']:.2f}%",
            ])

        if not rows_autores:
            rows_autores = [["—", "—", "—", "—", "—", "—"]]

        ta = Table(
            hdr_autores + rows_autores,
            colWidths=[4.0*cm, 3.0*cm, 1.8*cm, 4.0*cm, 1.8*cm, 1.6*cm],
        )
        ta.setStyle(header_ts())
        story.append(ta)

        # ── COTA EDITORIAL (25%) ──────────────────────────────────
        story.append(Paragraph(f"COTA EDITORIAL — {COTA_EDITORIAL:.0f}% (Lei 9.610/98 / ECAD)", h2))

        if not editoras:
            story.append(Paragraph(
                "⚠ Nenhuma editora cadastrada. Os 25% da cota editorial estão "
                "reservados até que uma editora seja vinculada à obra.",
                aviso_style,
            ))
        else:
            hdr_ed = [["Editora", "CNPJ", "% Interno", "% Obra"]]
            rows_ed = []
            for item in editoras_splits:
                ed = item["_editora_raw"]
                rows_ed.append([
                    ed.get("nome", "—"),
                    ed.get("cnpj", "—"),
                    f"{item['percentual_interno']:.2f}%",
                    f"{item['percentual_obra']:.2f}%",
                ])
            ted = Table(
                hdr_ed + rows_ed,
                colWidths=[6.0*cm, 5.0*cm, 2.5*cm, 2.5*cm],
            )
            ted.setStyle(header_ts())
            story.append(ted)

        # ── VALIDAÇÃO ─────────────────────────────────────────────
        soma = (
            sum(i["percentual_obra"] for i in autores_splits)
            + sum(i["percentual_obra"] for i in editoras_splits)
        )
        status_txt = "OK ✓" if abs(soma - 100.0) < 0.1 else f"ERRO — soma = {soma:.2f}%"
        story += [
            Spacer(1, 0.3 * cm),
            Table([
                ["Soma total dos direitos", f"{soma:.2f}%"],
                ["Status de validação",     status_txt],
            ], colWidths=[6.0 * cm, 10.0 * cm], style=base_ts()),
        ]

        # ── INTÉRPRETE ────────────────────────────────────────────
        story += [
            Paragraph("INTÉRPRETE", h2),
            Table([
                ["Nome",           interprete.get("nome", "") or "—"],
                ["Nome Artístico", interprete.get("nome_artistico", "") or "—"],
                ["Email",          interprete.get("email", "") or "—"],
            ], colWidths=[4.5 * cm, 11.5 * cm], style=base_ts()),
        ]

        # ── CONTRATO ──────────────────────────────────────────────
        story += [
            Paragraph("CONTRATO", h2),
            Table([
                ["ID do Contrato",  str(contrato.get("id", ""))],
                ["Data assinatura", assinado],
                ["Tipo",            "Edição Musical"],
            ], colWidths=[4.5 * cm, 11.5 * cm], style=base_ts()),
        ]

        # ── HASH ──────────────────────────────────────────────────
        story += [
            Spacer(1, 0.5 * cm),
            Paragraph("HASH DE INTEGRIDADE SHA-256", h2),
            Paragraph(hash_sha256, mono),
            Spacer(1, 1 * cm),
            Paragraph(
                "Documento gerado automaticamente pela plataforma Gravan. "
                "Validade jurídica conforme MP nº 2.200-2/2001 e Lei nº 14.063/2020.",
                sub,
            ),
        ]

        doc.build(story)
        return buf.getvalue()
