"""
Rotas para gerenciar AGREGADOS de uma editora.
- GET    /api/agregados                 lista agregados da editora logada
- POST   /api/agregados                 vincula artista existente OU cria ghost user
- GET    /api/agregados/<id>            detalhes de um agregado
- DELETE /api/agregados/<id>            desvincula (publisher_id = NULL)
- GET    /api/agregados/<id>/dashboard  dashboard do agregado (visão da editora)
"""
import secrets
from datetime import datetime, timezone

from flask import Blueprint, request, jsonify, g, abort

from middleware.auth import require_auth
from db.supabase_client import get_supabase
from utils.audit import log_event
from utils.crypto import encrypt_pii

agregados_bp = Blueprint("agregados", __name__, url_prefix="/api/agregados")


def _ensure_publisher(sb):
    me = sb.table("perfis").select("id,role").eq("id", g.user.id).single().execute()
    if not me.data or me.data.get("role") != "publisher":
        return None
    return me.data


@agregados_bp.get("")
@require_auth
def listar():
    sb = get_supabase()
    if not _ensure_publisher(sb):
        abort(403, description="Apenas editoras")

    r = sb.table("perfis").select(
        "id,nome_completo,nome_artistico,email,is_ghost,agregado_desde"
    ).eq("publisher_id", g.user.id).order("agregado_desde", desc=True).execute()

    return jsonify(r.data or [])


@agregados_bp.post("")
@require_auth
def criar_ou_vincular():
    """
    Body: { nome_completo, nome_artistico, rg, cpf, email,
            endereco_rua, endereco_numero, endereco_bairro,
            endereco_cidade, endereco_uf, endereco_cep, endereco_compl? }

    Lógica:
      1. Procura perfil por email
      2. Se existir → atualiza publisher_id (vincula)
      3. Se não existir → cria ghost user (auth + perfil) e vincula
    """
    data = request.get_json(silent=True) or {}
    obrigatorios = ["nome_completo", "nome_artistico", "rg", "cpf", "email"]
    faltam = [c for c in obrigatorios if not data.get(c)]
    if faltam:
        abort(400, description=f"Campos obrigatórios faltando: {', '.join(faltam)}")

    sb = get_supabase()
    if not _ensure_publisher(sb):
        abort(403, description="Apenas editoras")

    email = data["email"].strip().lower()

    # 1. Procura perfil existente
    existing = sb.table("perfis").select("id,publisher_id,is_ghost,nome_completo").eq("email", email).maybe_single().execute()

    if existing and existing.data:
        perfil = existing.data
        if perfil.get("publisher_id") and perfil["publisher_id"] != g.user.id:
            abort(409, description="Este artista já está agregado a outra editora")

        sb.table("perfis").update({
            "publisher_id":   g.user.id,
            "agregado_desde": datetime.now(timezone.utc).isoformat(),
        }).eq("id", perfil["id"]).execute()

        log_event("agregado.vinculado", entity_type="perfil", entity_id=perfil["id"],
                  metadata={"editora_id": g.user.id, "modo": "vinculacao", "email": email})

        return jsonify({"id": perfil["id"], "modo": "vinculado", "is_ghost": perfil.get("is_ghost", False)})

    # 2. Cria ghost user via Supabase Admin API
    senha_temp = secrets.token_urlsafe(24)
    invite_token = secrets.token_urlsafe(32)
    try:
        novo_auth = sb.auth.admin.create_user({
            "email":         email,
            "password":      senha_temp,
            "email_confirm": False,
            "user_metadata": {"ghost": True, "publisher_id": g.user.id},
        })
        novo_id = novo_auth.user.id
    except Exception as e:
        abort(400, description=f"Não foi possível criar usuário: {e}")

    perfil_payload = {
        "id":               novo_id,
        "email":            email,
        "nome_completo":    data["nome_completo"].strip(),
        "nome_artistico":   data["nome_artistico"].strip(),
        "rg":               encrypt_pii(data["rg"].strip()),
        "cpf":              encrypt_pii(data["cpf"].strip()),
        "endereco_rua":     (data.get("endereco_rua") or "").strip(),
        "endereco_numero":  (data.get("endereco_numero") or "").strip(),
        "endereco_compl":   (data.get("endereco_compl") or "").strip(),
        "endereco_bairro":  (data.get("endereco_bairro") or "").strip(),
        "endereco_cidade":  (data.get("endereco_cidade") or "").strip(),
        "endereco_uf":      (data.get("endereco_uf") or "").strip().upper()[:2],
        "endereco_cep":     (data.get("endereco_cep") or "").strip(),
        "role":             "artist",
        "publisher_id":     g.user.id,
        "agregado_desde":   datetime.now(timezone.utc).isoformat(),
        "is_ghost":         True,
        "ghost_invite_token":   invite_token,
        "ghost_invite_sent_at": datetime.now(timezone.utc).isoformat(),
    }
    sb.table("perfis").insert(perfil_payload).execute()

    log_event("usuario.ghost_criado", entity_type="perfil", entity_id=novo_id,
              metadata={"editora_id": g.user.id, "email": email})
    log_event("agregado.vinculado", entity_type="perfil", entity_id=novo_id,
              metadata={"editora_id": g.user.id, "modo": "ghost_criado"})

    return jsonify({
        "id":            novo_id,
        "modo":          "ghost_criado",
        "is_ghost":      True,
        "invite_token":  invite_token,
    })


@agregados_bp.get("/<aid>")
@require_auth
def detalhes(aid):
    sb = get_supabase()
    if not _ensure_publisher(sb):
        abort(403, description="Apenas editoras")

    r = sb.table("perfis").select("*").eq("id", aid).eq("publisher_id", g.user.id).maybe_single().execute()
    if not r or not r.data:
        abort(404, description="Agregado não encontrado")
    return jsonify(r.data)


@agregados_bp.delete("/<aid>")
@require_auth
def desvincular(aid):
    sb = get_supabase()
    if not _ensure_publisher(sb):
        abort(403, description="Apenas editoras")

    r = sb.table("perfis").select("id,publisher_id").eq("id", aid).maybe_single().execute()
    if not r or not r.data or r.data.get("publisher_id") != g.user.id:
        abort(404, description="Agregado não encontrado")

    sb.table("perfis").update({"publisher_id": None, "agregado_desde": None}).eq("id", aid).execute()
    log_event("agregado.removido", entity_type="perfil", entity_id=aid,
              metadata={"editora_id": g.user.id})
    return jsonify({"ok": True})


@agregados_bp.get("/<aid>/dashboard")
@require_auth
def dashboard_agregado(aid):
    """Dashboard do agregado, visto pela editora."""
    sb = get_supabase()
    if not _ensure_publisher(sb):
        abort(403, description="Apenas editoras")

    perfil = sb.table("perfis").select("id,nome_completo,nome_artistico,publisher_id").eq("id", aid).maybe_single().execute()
    if not perfil or not perfil.data or perfil.data.get("publisher_id") != g.user.id:
        abort(403, description="Agregado não pertence a esta editora")

    obras_autoria = sb.table("obras_autores").select("obra_id").eq("perfil_id", aid).execute()
    obras_ids = list({o["obra_id"] for o in (obras_autoria.data or [])})

    obras = []
    if obras_ids:
        obras = sb.table("obras").select("id,titulo,publicada,created_at").in_("id", obras_ids).execute().data or []

    contratos = sb.table("contracts_edicao").select("*").eq("autor_id", aid).execute()

    ganhos_total = 0
    ganhos_retidos = 0
    try:
        repasses = sb.table("repasses").select("valor_cents,status").eq("perfil_id", aid).execute()
        ganhos_total = sum(r.get("valor_cents", 0) for r in (repasses.data or []) if r["status"] == "enviado")
        ganhos_retidos = sum(r.get("valor_cents", 0) for r in (repasses.data or []) if r["status"] == "retido")
    except Exception:
        pass

    return jsonify({
        "perfil":           perfil.data,
        "total_obras":      len(obras),
        "obras":            obras,
        "contratos":        contratos.data or [],
        "ganhos_cents":     ganhos_total,
        "ganhos_retidos_cents": ganhos_retidos,
    })
