"""
Rotas para listar e assinar Contratos de Edição (autor ↔ editora).
- GET  /api/contratos-edicao                  lista contratos do usuário (autor ou editora)
- GET  /api/contratos-edicao/<id>             detalhes
- POST /api/contratos-edicao/<id>/assinar     assina (autor OU editora, conforme quem chamou)
"""
import hashlib
from datetime import datetime, timezone

from flask import Blueprint, request, jsonify, g, abort

from middleware.auth import require_auth
from db.supabase_client import get_supabase
from utils.audit import log_event

contratos_edicao_bp = Blueprint("contratos_edicao", __name__, url_prefix="/api/contratos-edicao")


def _hash_ip(ip):
    return hashlib.sha256(ip.encode()).hexdigest()[:32] if ip else None


@contratos_edicao_bp.get("")
@require_auth
def listar():
    sb = get_supabase()
    role_q = sb.table("perfis").select("role").eq("id", g.user.id).single().execute()
    role = (role_q.data or {}).get("role")

    if role == "publisher":
        r = sb.table("contracts_edicao").select(
            "id,obra_id,autor_id,share_pct,status,created_at,signed_by_publisher_at,signed_by_autor_at"
        ).eq("publisher_id", g.user.id).order("created_at", desc=True).execute()
    else:
        r = sb.table("contracts_edicao").select(
            "id,obra_id,publisher_id,share_pct,status,created_at,signed_by_publisher_at,signed_by_autor_at"
        ).eq("autor_id", g.user.id).order("created_at", desc=True).execute()

    return jsonify(r.data or [])


@contratos_edicao_bp.get("/<cid>")
@require_auth
def detalhes(cid):
    sb = get_supabase()
    r = sb.table("contracts_edicao").select("*").eq("id", cid).maybe_single().execute()
    if not r or not r.data:
        abort(404, description="Contrato não encontrado")
    c = r.data
    if g.user.id not in (c["autor_id"], c["publisher_id"]):
        adm = sb.table("perfis").select("role").eq("id", g.user.id).single().execute()
        if (adm.data or {}).get("role") != "administrador":
            abort(403, description="Sem acesso a este contrato")
    return jsonify(c)


@contratos_edicao_bp.post("/<cid>/assinar")
@require_auth
def assinar(cid):
    sb = get_supabase()
    r = sb.table("contracts_edicao").select("*").eq("id", cid).maybe_single().execute()
    if not r or not r.data:
        abort(404, description="Contrato não encontrado")
    c = r.data

    if c["status"] in ("assinado", "cancelado"):
        abort(400, description=f"Contrato já está {c['status']}")

    ip_hash = _hash_ip(request.headers.get("X-Forwarded-For", request.remote_addr))
    agora = datetime.now(timezone.utc).isoformat()

    update = {}
    if g.user.id == c["autor_id"] and not c.get("signed_by_autor_at"):
        update["signed_by_autor_at"] = agora
        update["autor_ip_hash"] = ip_hash
    elif g.user.id == c["publisher_id"] and not c.get("signed_by_publisher_at"):
        update["signed_by_publisher_at"] = agora
        update["publisher_ip_hash"] = ip_hash
    else:
        abort(403, description="Você não é parte deste contrato ou já assinou")

    autor_ok = bool(update.get("signed_by_autor_at") or c.get("signed_by_autor_at"))
    pub_ok   = bool(update.get("signed_by_publisher_at") or c.get("signed_by_publisher_at"))

    if autor_ok and pub_ok:
        update["status"] = "assinado"
        update["completed_at"] = agora
    else:
        update["status"] = "assinado_parcial"

    sb.table("contracts_edicao").update(update).eq("id", cid).execute()

    log_event("contrato.assinado", entity_type="contract_edicao", entity_id=cid,
              metadata={"parte": "autor" if g.user.id == c["autor_id"] else "publisher",
                        "status_final": update["status"]})

    atualizado = sb.table("contracts_edicao").select("*").eq("id", cid).single().execute()
    return jsonify(atualizado.data)
