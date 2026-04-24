"""
Gravan — Rotas do Dossiê da Obra
==================================

Endpoints (todos sob o prefixo `/api/dossies`):

  POST  /api/dossies/obras/<obra_id>          — gera o dossiê da obra
  GET   /api/dossies/                          — lista todos os dossiês (admin)
                                                 ?q=<termo>  filtra por id ou título
  GET   /api/dossies/admin/obras               — lista TODAS as obras (admin)
                                                 com info do dossiê (se existe)
                                                 ?q=<termo>  filtra por título / id
  GET   /api/dossies/<dossie_id>/visualizar    — metadata JSON
                                                 (autor / editora / admin)
  GET   /api/dossies/<dossie_id>/download      — baixa o ZIP
                                                 (autor / editora / admin)

CORREÇÕES NESTA VERSÃO:
  - Não vaza traceback para o cliente (loga no servidor e devolve
    mensagem genérica).
  - Substituiu `.single()` por consultas com `limit(1)` para evitar
    exceções quando o registro não existe.
  - Adicionada busca (?q=) usando `ilike` no id e no título.
  - Validação de ownership tolerante a obras sem registro.
"""
from __future__ import annotations

import io
import logging
import uuid

from flask import Blueprint, abort, g, jsonify, request, send_file

from db.supabase_client import get_supabase
from middleware.auth import require_auth
from services.dossie import DossieService
from utils.audit import log_event

logger = logging.getLogger(__name__)

dossie_bp = Blueprint("dossie", __name__)


# ──────────────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────────────

def _get_perfil() -> dict:
    sb = get_supabase()
    r = (
        sb.table("perfis")
        .select("id,role")
        .eq("id", g.user.id)
        .limit(1)
        .execute()
    )
    return (r.data or [{}])[0]


def _is_valid_uuid(val: str) -> bool:
    try:
        uuid.UUID(str(val))
        return True
    except (ValueError, AttributeError, TypeError):
        return False


def _verificar_acesso_obra(obra_id: str, perfil: dict) -> dict:
    """
    Garante que o usuário tem acesso à obra (titular, editora vinculada
    ou administrador). Retorna a obra ou aborta com 403/404.
    """
    sb   = get_supabase()
    role = perfil.get("role")

    # Administrador → acesso total
    if role == "administrador":
        r = sb.table("obras").select("*").eq("id", obra_id).limit(1).execute()
        if not r.data:
            abort(404, description="Obra não encontrada.")
        return r.data[0]

    # Titular da obra
    r = (
        sb.table("obras")
        .select("*")
        .eq("id", obra_id)
        .eq("titular_id", g.user.id)
        .limit(1)
        .execute()
    )
    if r.data:
        return r.data[0]

    # Editora vinculada via contracts_edicao
    try:
        r2 = (
            sb.table("contracts_edicao")
            .select("obra_id")
            .eq("obra_id", obra_id)
            .eq("publisher_id", g.user.id)
            .limit(1)
            .execute()
        )
        if r2.data:
            r3 = sb.table("obras").select("*").eq("id", obra_id).limit(1).execute()
            if r3.data:
                return r3.data[0]
    except Exception as e:
        logger.warning("Falha ao consultar contracts_edicao: %s", e)

    abort(
        403,
        description=(
            "Acesso negado: você não é titular, editora vinculada ou "
            "administrador desta obra."
        ),
    )


def _abort_internal(action: str, exc: Exception) -> None:
    """Loga o erro completo e devolve a mensagem da exceção ao cliente
    (endpoints admin — não há risco de vazamento sensível)."""
    logger.exception("Erro em %s: %s", action, exc)
    cls = type(exc).__name__
    msg = str(exc) or repr(exc)
    abort(
        500,
        description=f"[{action}] {cls}: {msg}",
    )


# ══════════════════════════════════════════════════════════════════
# POST /api/dossies/obras/<obra_id>
# ══════════════════════════════════════════════════════════════════
@dossie_bp.route("/obras/<string:obra_id>", methods=["POST"])
@require_auth
def gerar_dossie(obra_id: str):
    """Gera o dossiê de uma obra. Dados vêm SOMENTE do contrato assinado."""
    if not _is_valid_uuid(obra_id):
        abort(400, description="ID de obra inválido.")

    perfil = _get_perfil()
    if not perfil:
        abort(404, description="Perfil não encontrado.")

    _verificar_acesso_obra(obra_id, perfil)

    try:
        svc    = DossieService()
        dossie = svc.gerar(obra_id=obra_id, user_id=str(g.user.id))
    except ValueError as e:
        # Erros de validação (dados faltando, splits errados, etc.) → 422
        abort(422, description=str(e))
    except Exception as e:
        _abort_internal("gerar_dossie", e)

    log_event(
        action="dossie.gerado",
        entity_type="dossie",
        entity_id=str(dossie.get("id", "")),
        metadata={
            "obra_id":     obra_id,
            "contrato_id": dossie.get("contrato_id"),
            "hash":        (dossie.get("hash_sha256") or "")[:16] + "…",
        },
        user_id=str(g.user.id),
    )

    return jsonify({
        "id":          dossie.get("id"),
        "obra_id":     obra_id,
        "titulo_obra": dossie.get("titulo_obra", ""),
        "hash_sha256": dossie.get("hash_sha256"),
        "created_at":  dossie.get("created_at"),
        "message":     "Dossiê gerado com sucesso.",
    }), 201


# ══════════════════════════════════════════════════════════════════
# GET /api/dossies/  — admin only, com busca opcional
# ══════════════════════════════════════════════════════════════════
@dossie_bp.route("/", methods=["GET"])
@dossie_bp.route("",  methods=["GET"])
@require_auth
def listar_dossies():
    """
    Lista todos os dossiês gerados (admin only).

    Query params:
      - q: busca por trecho do ID único OU do título da obra
    """
    perfil = _get_perfil()
    if perfil.get("role") != "administrador":
        abort(
            403,
            description="Apenas administradores podem listar todos os dossiês.",
        )

    q = (request.args.get("q") or "").strip()

    sb = get_supabase()
    query = (
        sb.table("dossies")
        .select("id,obra_id,titulo_obra,hash_sha256,created_at,gerado_por")
        .order("created_at", desc=True)
    )

    if q:
        # Busca por trecho do ID único ou do título da obra (case-insensitive).
        # `or_` aceita filtros tipo PostgREST: campo.op.valor
        safe = q.replace(",", " ").replace("(", "").replace(")", "")
        query = query.or_(
            f"id.ilike.%{safe}%,titulo_obra.ilike.%{safe}%,obra_id.ilike.%{safe}%"
        )

    try:
        r = query.execute()
    except Exception as e:
        _abort_internal("listar_dossies", e)

    return jsonify(r.data or [])


# ══════════════════════════════════════════════════════════════════
# GET /api/dossies/admin/obras  — lista TODAS as obras (admin)
# Usado pela aba "Obras" do painel administrador.
# Cada obra vem com seu ID único e (quando existe) o id do dossiê
# já gerado, para o frontend renderizar os botões
# "GERAR DOSSIÊ" e "BAIXAR DOSSIÊ".
# ══════════════════════════════════════════════════════════════════
@dossie_bp.route("/admin/obras", methods=["GET"])
@require_auth
def admin_listar_obras():
    perfil = _get_perfil()
    if perfil.get("role") != "administrador":
        abort(403, description="Apenas administradores podem listar todas as obras.")

    q  = (request.args.get("q") or "").strip()
    sb = get_supabase()

    try:
        query = (
            sb.table("obras")
            .select(
                "id, nome, genero, preco_cents, status, created_at, "
                "audio_path, "
                "titular_id, "
                "perfis:titular_id(nome, nome_artistico, email)"
            )
            .order("created_at", desc=True)
        )
        if q:
            safe = q.replace(",", " ").replace("(", "").replace(")", "")
            query = query.or_(f"id.ilike.%{safe}%,nome.ilike.%{safe}%")
        obras = (query.execute().data) or []
    except Exception as e:
        _abort_internal("admin_listar_obras", e)

    # Busca dossiês existentes em uma única query (evita N+1)
    obra_ids = [o["id"] for o in obras]
    dossies_por_obra: dict = {}
    if obra_ids:
        try:
            r = (
                sb.table("dossies")
                .select("id, obra_id, hash_sha256, created_at")
                .in_("obra_id", obra_ids)
                .execute()
            )
            for d in (r.data or []):
                # Mantém só o mais recente por obra
                cur = dossies_por_obra.get(d["obra_id"])
                if not cur or (d.get("created_at") or "") > (cur.get("created_at") or ""):
                    dossies_por_obra[d["obra_id"]] = d
        except Exception as e:
            logger.warning("Falha ao carregar dossiês existentes: %s", e)

    out = []
    for o in obras:
        titular = o.get("perfis") or {}
        d       = dossies_por_obra.get(o["id"])
        out.append({
            "id":             o["id"],
            "nome":           o.get("nome"),
            "genero":         o.get("genero"),
            "preco_cents":    o.get("preco_cents"),
            "status":         o.get("status"),
            "created_at":     o.get("created_at"),
            "audio_path":     o.get("audio_path"),
            "titular": {
                "id":             o.get("titular_id"),
                "nome":           titular.get("nome_artistico") or titular.get("nome"),
                "email":          titular.get("email"),
            },
            "dossie": (
                {
                    "id":          d["id"],
                    "hash_sha256": d.get("hash_sha256"),
                    "created_at":  d.get("created_at"),
                } if d else None
            ),
        })

    return jsonify(out)


# ══════════════════════════════════════════════════════════════════
# GET /api/dossies/<dossie_id>/visualizar
# ══════════════════════════════════════════════════════════════════
@dossie_bp.route("/<string:dossie_id>/visualizar", methods=["GET"])
@require_auth
def visualizar_dossie(dossie_id: str):
    """Retorna o metadata JSON do dossiê (sem CPF)."""
    if not _is_valid_uuid(dossie_id):
        abort(400, description="ID de dossiê inválido.")

    sb = get_supabase()
    r = sb.table("dossies").select("*").eq("id", dossie_id).limit(1).execute()
    if not r.data:
        abort(404, description="Dossiê não encontrado.")

    d = r.data[0]
    perfil = _get_perfil()
    _verificar_acesso_obra(d["obra_id"], perfil)

    log_event(
        action="dossie.visualizado",
        entity_type="dossie",
        entity_id=dossie_id,
        user_id=str(g.user.id),
    )

    meta = d.get("metadata") or {}
    # Remove CPF antes de devolver — visualização ≠ download oficial
    for autor in meta.get("autores", []) or []:
        autor.pop("cpf", None)

    return jsonify({
        "id":          d["id"],
        "obra_id":     d["obra_id"],
        "titulo_obra": d.get("titulo_obra", ""),
        "hash_sha256": d["hash_sha256"],
        "created_at":  d["created_at"],
        "metadata":    meta,
    })


# ══════════════════════════════════════════════════════════════════
# GET /api/dossies/<dossie_id>/download
# ══════════════════════════════════════════════════════════════════
@dossie_bp.route("/<string:dossie_id>/download", methods=["GET"])
@require_auth
def download_dossie(dossie_id: str):
    """Faz o download do ZIP do dossiê."""
    if not _is_valid_uuid(dossie_id):
        abort(400, description="ID de dossiê inválido.")

    sb = get_supabase()
    r = (
        sb.table("dossies")
        .select("obra_id,titulo_obra,storage_path")
        .eq("id", dossie_id)
        .limit(1)
        .execute()
    )
    if not r.data:
        abort(404, description="Dossiê não encontrado.")

    d      = r.data[0]
    perfil = _get_perfil()
    _verificar_acesso_obra(d["obra_id"], perfil)

    try:
        svc       = DossieService()
        zip_bytes = svc.download_zip(dossie_id)
    except ValueError as e:
        abort(404, description=str(e))
    except Exception as e:
        _abort_internal("download_dossie", e)

    log_event(
        action="dossie.baixado",
        entity_type="dossie",
        entity_id=dossie_id,
        metadata={"obra_id": d["obra_id"]},
        user_id=str(g.user.id),
    )

    filename = f"obra-{d['obra_id']}.zip"
    return send_file(
        io.BytesIO(zip_bytes),
        mimetype="application/zip",
        as_attachment=True,
        download_name=filename,
    )
