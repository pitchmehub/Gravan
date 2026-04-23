"""
Pitch.me — Serviço de Geração de Dossiê da Obra (Master Package)
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

CORREÇÕES NESTA VERSÃO (v3):
  - Hash agora é DETERMINÍSTICO: usa o texto do contrato (`conteudo`)
    em vez do PDF regenerado (que muda a cada execução por causa do
    timestamp embutido pelo ReportLab). Isso é fundamental para a
    "integridade jurídica" exigida pela especificação.
  - Adicionado o campo `interprete` no metadata.json (faltava).
  - Validação de splits com mensagem clara.
  - Idempotência: regerar o dossiê para a mesma obra substitui o
    arquivo anterior em vez de duplicar linha na tabela.
  - Corrigido `upsert` do Supabase Python (espera string "true").
  - Erros padronizados como `ValueError` para a rota tratar como 422.
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
EDITORA_NOME       = "PITCH.ME"
EDITORA_PERCENTUAL = 20          # informativo no metadata
ROYALTIES_DEFAULT  = {
    "ecad":      {"interprete": 10, "editora": 10, "autores": 80},
    "fonograma": 2,
}


class DossieService:
    def __init__(self) -> None:
        self.sb = get_supabase()

    # ──────────────────────────────────────────────────────────────
    # API PÚBLICA
    # ──────────────────────────────────────────────────────────────

    def gerar(self, obra_id: str, user_id: str) -> dict:
        """
        Gera o dossiê de uma obra e persiste no Storage + tabela `dossies`.

        Retorna a linha inserida na tabela `dossies` (com `id` único).
        """
        obra        = self._buscar_obra(obra_id)
        contrato    = self._buscar_contrato_assinado(obra_id)
        autores     = self._buscar_autores(obra_id)
        interprete  = self._extrair_interprete(contrato)
        audio_bytes = self._download_audio(obra["audio_path"])

        # 1) Monta metadata SEM o hash (será adicionado depois)
        metadata = self._montar_metadata(obra, autores, interprete, contrato)

        # 2) Hash determinístico: depende SOMENTE de dados estáveis
        #    (metadata canônico + texto do contrato assinado).
        #    Não usa o PDF gerado, pois ele tem timestamp variável.
        contrato_texto = (contrato.get("conteudo") or "").encode("utf-8")
        metadata_canon = json.dumps(
            metadata, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        hash_sha256 = hashlib.sha256(metadata_canon + contrato_texto).hexdigest()

        # 3) Anexa o hash e serializa a versão final (humano-legível)
        metadata["hash_integridade"] = hash_sha256
        metadata_json = json.dumps(metadata, ensure_ascii=False, indent=2)

        # 4) Gera os artefatos secundários
        contrato_pdf = gerar_pdf_contrato(contrato)
        resumo_pdf   = self._gerar_resumo_pdf(
            obra, autores, interprete, contrato, hash_sha256
        )

        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        hash_txt = (
            f"HASH SHA256:\n{hash_sha256}\n\n"
            f"Data de geração:\n{ts}\n"
        )

        # 5) Compacta tudo
        zip_bytes = self._criar_zip(
            audio_bytes   = audio_bytes,
            letra         = obra.get("letra", "") or "",
            metadata_json = metadata_json,
            contrato_pdf  = contrato_pdf,
            resumo_pdf    = resumo_pdf,
            hash_txt      = hash_txt,
        )

        # 6) Sobe para o Storage (upsert — substitui se já existir)
        storage_path = f"dossies/{obra_id}/obra-{obra_id}.zip"
        self.sb.storage.from_("dossies").upload(
            path=storage_path,
            file=zip_bytes,
            file_options={
                "content-type": "application/zip",
                # supabase-py exige string "true"/"false" aqui
                "upsert": "true",
            },
        )

        # 7) Idempotência: se já existe um dossiê para esta obra,
        #    apaga o anterior antes de inserir o novo.
        try:
            self.sb.table("dossies").delete().eq("obra_id", obra_id).execute()
        except Exception:
            # se a tabela está vazia ou políticas RLS impedem, segue.
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
        """Retorna os bytes do ZIP de um dossiê já gerado."""
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

    def _buscar_contrato_assinado(self, obra_id: str) -> dict:
        """
        Busca o contrato de edição assinado pelo titular ao cadastrar
        a obra.

        Tabela correta: `contratos_edicao` (não confundir com
        `contracts_edicao`, que é entre compositores e editoras
        externas).
        """
        r = (
            self.sb.table("contratos_edicao")
            .select("*")
            .eq("obra_id", obra_id)
            .limit(1)
            .execute()
        )
        if not r.data:
            raise ValueError(
                "Contrato de edição não encontrado para esta obra. "
                "O dossiê só pode ser gerado para obras cujo contrato "
                "de edição foi registrado na plataforma Pitch.me."
            )
        contrato = r.data[0]
        if not contrato.get("assinado_em"):
            dados = contrato.get("dados_titular") or {}
            contrato["assinado_em"] = dados.get("data_assinatura") or ""
        return contrato

    def _buscar_autores(self, obra_id: str) -> list:
        """
        Lê os autores em `coautorias` (fluxo atual) com fallback para
        `obras_autores` (legado), e valida que os splits dos autores
        somam 100%.
        """
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
                .select("*, perfis(id,nome,nome_artistico,email,cpf)")
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
                .select("*, perfis(id,nome,nome_artistico,email,cpf)")
                .eq("obra_id", obra_id)
                .execute()
            )
            return r.data or []
        except Exception:
            return []

    def _extrair_interprete(self, contrato: dict) -> dict:
        """
        Extrai o intérprete do contrato. Procura nos campos:
          - contrato.interprete (objeto)
          - contrato.dados_titular.interprete
          - contrato.dados_titular  (titular = intérprete em muitos casos)
        Sempre retorna um dicionário (mesmo vazio).
        """
        if isinstance(contrato.get("interprete"), dict):
            i = contrato["interprete"]
        else:
            dados = contrato.get("dados_titular") or {}
            if isinstance(dados.get("interprete"), dict):
                i = dados["interprete"]
            else:
                i = dados  # fallback: usa o titular como intérprete
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
    # MONTAGEM DE METADATA / RESUMO
    # ──────────────────────────────────────────────────────────────

    def _montar_metadata(
        self,
        obra: dict,
        autores: list,
        interprete: dict,
        contrato: dict,
    ) -> dict:
        autores_list = []
        for a in autores:
            p = a.get("perfis") or {}
            cpf_raw = p.get("cpf") or ""
            try:
                cpf = decrypt_pii(cpf_raw) if cpf_raw else ""
            except Exception:
                cpf = ""
            autores_list.append({
                "nome":           p.get("nome", "") or "",
                "nome_artistico": p.get("nome_artistico") or "",
                "cpf":            cpf,
                "email":          p.get("email", "") or "",
                "percentual":     float(a.get("share_pct", 0) or 0),
                "funcao":         "Autor" if a.get("is_principal") else "Coautor",
            })

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
            "editora": {
                "nome":       EDITORA_NOME,
                "percentual": EDITORA_PERCENTUAL,
            },
            "autores":    autores_list,
            "interprete": interprete,
            "royalties":  ROYALTIES_DEFAULT,
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
        interprete: dict,
        contrato: dict,
        hash_sha256: str,
    ) -> bytes:
        buf = io.BytesIO()
        doc = SimpleDocTemplate(
            buf, pagesize=A4,
            leftMargin=2.2 * cm, rightMargin=2.2 * cm,
            topMargin=2.0 * cm, bottomMargin=2.0 * cm,
            title="Resumo do Dossiê — Pitch.me",
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

        def ts() -> TableStyle:
            return TableStyle([
                ("FONTNAME",      (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE",      (0, 0), (-1, -1), 9),
                ("TEXTCOLOR",     (0, 0), (0, -1),  colors.HexColor("#555555")),
                ("BACKGROUND",    (0, 0), (0, -1),  colors.HexColor("#F5F5F5")),
                ("GRID",          (0, 0), (-1, -1), 0.3, colors.HexColor("#DDDDDD")),
                ("TOPPADDING",    (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ])

        assinado = str(
            contrato.get("assinado_em") or contrato.get("created_at") or ""
        )[:10]

        story = [
            Paragraph("DOSSIÊ DA OBRA", h1),
            Paragraph(
                "Pitch.me · Documento Oficial de Integridade Musical", sub
            ),
            Paragraph("OBRA", h2),
            Table([
                ["Título",           obra.get("nome", "—") or "—"],
                ["Gênero",           obra.get("genero")    or "—"],
                ["ID",               str(obra.get("id", ""))],
                ["Data de cadastro", str(obra.get("created_at", ""))[:10]],
            ], colWidths=[4.5 * cm, 11.5 * cm], style=ts()),

            Paragraph("AUTORES E SPLITS", h2),
        ]

        hdr = [["Nome", "Nome Artístico", "Email", "%"]]
        rows = []
        for a in autores:
            p = a.get("perfis") or {}
            rows.append([
                p.get("nome", "—") or "—",
                p.get("nome_artistico") or "—",
                p.get("email", "—") or "—",
                f"{float(a.get('share_pct', 0) or 0):.1f}%",
            ])
        if not rows:
            rows = [["—", "—", "—", "—"]]
        ta = Table(hdr + rows, colWidths=[4 * cm, 4 * cm, 5 * cm, 3 * cm])
        ta.setStyle(TableStyle([
            ("FONTNAME",      (0, 0), (-1, -1), "Helvetica"),
            ("FONTSIZE",      (0, 0), (-1, -1), 9),
            ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
            ("BACKGROUND",    (0, 0), (-1, 0),  colors.HexColor("#111111")),
            ("TEXTCOLOR",     (0, 0), (-1, 0),  colors.white),
            ("GRID",          (0, 0), (-1, -1), 0.3, colors.HexColor("#DDDDDD")),
            ("TOPPADDING",    (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(ta)

        story += [
            Paragraph("INTÉRPRETE", h2),
            Table([
                ["Nome",           interprete.get("nome", "") or "—"],
                ["Nome Artístico", interprete.get("nome_artistico", "") or "—"],
                ["Email",          interprete.get("email", "") or "—"],
            ], colWidths=[4.5 * cm, 11.5 * cm], style=ts()),

            Paragraph("EDITORA", h2),
            Table(
                [[EDITORA_NOME, f"{EDITORA_PERCENTUAL}%"]],
                colWidths=[12 * cm, 4 * cm], style=ts(),
            ),

            Paragraph("CONTRATO", h2),
            Table([
                ["ID do Contrato",  str(contrato.get("id", ""))],
                ["Data assinatura", assinado],
                ["Tipo",            "Edição Musical"],
            ], colWidths=[4.5 * cm, 11.5 * cm], style=ts()),

            Spacer(1, 0.5 * cm),
            Paragraph("HASH DE INTEGRIDADE SHA-256", h2),
            Paragraph(hash_sha256, mono),

            Spacer(1, 1 * cm),
            Paragraph(
                "Documento gerado automaticamente pela plataforma Pitch.me. "
                "Validade jurídica conforme MP nº 2.200-2/2001 e Lei nº "
                "14.063/2020.",
                sub,
            ),
        ]
        doc.build(story)
        return buf.getvalue()
