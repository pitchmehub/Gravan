"""
Service de Obras — lógica de negócio para cadastro e gestão.
Orquestra validação, storage de áudio e persistência.

CORREÇÕES DE VULNERABILIDADES:
- #4 (CRÍTICA): Path traversal protection com UUID validation
- #16 (MÉDIA): Length validation
"""
import uuid
import hashlib
from flask import abort
from db.supabase_client import get_supabase
from utils.audio_validator import validate_mp3, MAX_AUDIO_BYTES
from utils.sanitizer import sanitize_obra_fields
from utils.validators import validate_uuid
from utils.audit import AuditLogger

AUDIO_BUCKET = "obras-audio"  # bucket privado no Supabase Storage


class ObraService:

    def __init__(self):
        self.sb = get_supabase()

    # ----------------------------------------------------------
    # Cadastrar nova obra
    # ----------------------------------------------------------
    def criar_obra(
        self,
        titular_id: str,
        nome: str,
        letra: str,
        genero,
        preco_cents: int,
        audio_bytes: bytes,
        coautorias: list,
        termos_aceitos: bool = False,  # [{perfil_id, share_pct}]
        obra_editada_terceiros: bool = False,
        editora_terceira_nome: str | None = None,
        editora_terceira_email: str | None = None,
        editora_terceira_telefone: str | None = None,
        editora_terceira_id: str | None = None,
    ) -> dict:
        """
        Fluxo completo de cadastro:
        1. Valida IDs (path traversal protection)
        2. Sanitiza campos de texto
        3. Valida arquivo de áudio (Magic Number + tamanho)
        4. Valida regras de coautoria
        5. Salva obra no DB
        6. Faz upload do áudio no Storage privado
        7. Insere coautorias
        8. Log de auditoria
        """
        if not validate_uuid(titular_id):
            abort(422, description="ID de titular inválido.")

        # 1. Sanitização
        campos = sanitize_obra_fields({"nome": nome, "letra": letra, "genero": genero})

        # 2. Validação do áudio
        valido, erro = validate_mp3(audio_bytes)
        if not valido:
            abort(422, description=erro)

        # 2.1. Hash do audio e da letra (detecção de duplicata)
        audio_hash = hashlib.md5(audio_bytes).hexdigest()
        letra_hash = hashlib.md5((campos["letra"] or "").strip().lower().encode("utf-8")).hexdigest()

        # 2.2. Verificar duplicata por AUDIO
        dup_audio = self.sb.table("obras").select("id, nome, titular_id").eq("audio_hash", audio_hash).execute()
        if dup_audio.data:
            nome_dup = dup_audio.data[0].get("nome", "")
            abort(409, description=f"Este arquivo de audio ja foi cadastrado na plataforma (obra: '{nome_dup}'). Nao e permitido cadastrar a mesma composicao duas vezes.")

        # 2.3. Verificar duplicata por LETRA
        dup_letra = self.sb.table("obras").select("id, nome").eq("letra_hash", letra_hash).execute()
        if dup_letra.data:
            nome_dup = dup_letra.data[0].get("nome", "")
            abort(409, description=f"A letra desta composicao ja foi cadastrada (obra: '{nome_dup}'). Cada letra so pode ser registrada uma vez.")

        # 3. Validação de coautorias
        self._validar_coautorias(titular_id, coautorias)

        # 4. Inserir obra
        obra_resp = (
            self.sb.table("obras")
            .insert({
                "nome":             campos["nome"],
                "letra":            campos["letra"],
                "genero":           campos["genero"],
                "titular_id":       titular_id,
                "preco_cents":      preco_cents,
                "audio_bytes":      len(audio_bytes),
                "status":           "publicada",
                "termos_aceitos":   termos_aceitos,
                "termos_aceitos_em": "now()" if termos_aceitos else None,
                "audio_hash":       audio_hash,
                "letra_hash":       letra_hash,
                "obra_editada_terceiros":    bool(obra_editada_terceiros),
                "editora_terceira_nome":     editora_terceira_nome if obra_editada_terceiros else None,
                "editora_terceira_email":    (editora_terceira_email or "").lower() if obra_editada_terceiros else None,
                "editora_terceira_telefone": editora_terceira_telefone if obra_editada_terceiros else None,
                "editora_terceira_id":       editora_terceira_id if obra_editada_terceiros else None,
            })
            .execute()
        )
        obra = obra_resp.data[0]
        obra_id = obra["id"]

        # 5. Upload do áudio
        audio_path = f"{titular_id}/{obra_id}.mp3"
        self.sb.storage.from_(AUDIO_BUCKET).upload(
            path=audio_path,
            file=audio_bytes,
            file_options={"content-type": "audio/mpeg"},
        )
        self.sb.table("obras").update({"audio_path": audio_path}).eq("id", obra_id).execute()

        # 6. Inserir coautorias
        rows = [
            {
                "obra_id":    obra_id,
                "perfil_id":  c["perfil_id"],
                "share_pct":  c["share_pct"],
                "is_titular": c["perfil_id"] == titular_id,
            }
            for c in coautorias
        ]
        self.sb.table("coautorias").insert(rows).execute()

        # 7. Audit log
        AuditLogger.log_obra_criada(obra_id, campos["nome"])

        return obra

    # ----------------------------------------------------------
    # Publicar obra (muda status de rascunho → publicada)
    # ----------------------------------------------------------
    def publicar_obra(self, obra_id: str, titular_id: str) -> dict:
        obra = self._get_obra_ou_404(obra_id)
        if obra["titular_id"] != titular_id:
            abort(403, description="Apenas o titular pode publicar esta obra.")
        if obra["status"] == "publicada":
            abort(409, description="Obra já está publicada.")

        resp = (
            self.sb.table("obras")
            .update({"status": "publicada"})
            .eq("id", obra_id)
            .execute()
        )
        return resp.data[0]

    def obras_do_compositor(self, perfil_id: str) -> list[dict]:
        resp = (
            self.sb.table("coautorias")
            .select("obra_id, share_pct, is_titular, obras(*)")
            .eq("perfil_id", perfil_id)
            .execute()
        )
        return resp.data or []

    def catalogo_publico(self, genero: str | None = None, page: int = 1, per_page: int = 20) -> list[dict]:
        query = (
            self.sb.table("obras")
            .select("id, nome, genero, preco_cents, titular_id, perfis(nome, nivel)")
            .eq("status", "publicada")
            .order("created_at", desc=True)
            .range((page - 1) * per_page, page * per_page - 1)
        )
        if genero:
            query = query.eq("genero", genero)
        return query.execute().data or []

    # ----------------------------------------------------------
    # Helpers
    # ----------------------------------------------------------
    def _validar_coautorias(self, titular_id: str, coautorias: list[dict]) -> None:
        if not coautorias:
            abort(422, description="A obra deve ter pelo menos 1 compositor.")

        perfil_ids = [c["perfil_id"] for c in coautorias]

        if titular_id not in perfil_ids:
            abort(422, description="O titular deve estar incluído nas coautorias.")

        if len(perfil_ids) > 10:
            abort(422, description="Máximo de 10 compositores por obra.")

        if len(set(perfil_ids)) != len(perfil_ids):
            abort(422, description="Compositores duplicados na lista de coautorias.")

        total_pct = sum(float(c["share_pct"]) for c in coautorias)
        if round(total_pct, 2) != 100.0:
            abort(422, description=f"A soma dos splits deve ser 100%. Recebido: {total_pct:.2f}%")

    def _get_obra_ou_404(self, obra_id: str) -> dict:
        resp = self.sb.table("obras").select("*").eq("id", obra_id).single().execute()
        if not resp.data:
            abort(404, description="Obra não encontrada.")
        return resp.data
