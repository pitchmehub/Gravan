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

    contratos = r.data or []

    # Enriquece com nome da obra (busca em lote para eficiência)
    obra_ids = list({c["obra_id"] for c in contratos if c.get("obra_id")})
    obra_map = {}
    if obra_ids:
        try:
            ores = sb.table("obras").select("id,nome").in_("id", obra_ids).execute()
            obra_map = {o["id"]: o.get("nome") or "" for o in (ores.data or [])}
        except Exception:
            pass
    for c in contratos:
        c["obra_nome"] = obra_map.get(c.get("obra_id"), "")

    return jsonify(contratos)


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


GRAVAN_EDITORA_UUID = "e96bd8af-dfb8-4bf1-9ba5-7746207269cd"


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

    gravan_e_publisher = (c.get("publisher_id") == GRAVAN_EDITORA_UUID)

    update = {}
    if g.user.id == c["autor_id"] and not c.get("signed_by_autor_at"):
        update["signed_by_autor_at"] = agora
        update["autor_ip_hash"] = ip_hash
    elif g.user.id == c["publisher_id"] and not c.get("signed_by_publisher_at") and not gravan_e_publisher:
        update["signed_by_publisher_at"] = agora
        update["publisher_ip_hash"] = ip_hash
    else:
        abort(403, description="Você não é parte deste contrato ou já assinou")

    autor_ok = bool(update.get("signed_by_autor_at") or c.get("signed_by_autor_at"))
    # Gravan assina automaticamente na criação — considera sempre assinado pelo publisher
    pub_ok   = gravan_e_publisher or bool(update.get("signed_by_publisher_at") or c.get("signed_by_publisher_at"))

    if autor_ok and pub_ok:
        update["status"] = "assinado"
        update["completed_at"] = agora
    else:
        update["status"] = "assinado_parcial"

    sb.table("contracts_edicao").update(update).eq("id", cid).execute()

    log_event("contrato.assinado", entity_type="contract_edicao", entity_id=cid,
              metadata={"parte": "autor" if g.user.id == c["autor_id"] else "publisher",
                        "status_final": update["status"]})

    try:
        from services.notificacoes import notify
        # Nunca notifica o UUID fantasma da Gravan
        partes_reais = {pid for pid in (c["autor_id"], c["publisher_id"])
                        if pid and pid != GRAVAN_EDITORA_UUID}
        outra_parte = next((p for p in partes_reais if p != g.user.id), None)

        if update["status"] == "assinado":
            for pid in partes_reais:
                notify(
                    pid,
                    tipo="contrato_assinado",
                    titulo="Contrato de edição assinado",
                    mensagem="Todas as partes assinaram o contrato de edição.",
                    link=f"/contratos?contrato={cid}",
                    payload={"contract_id": cid, "tipo": "edicao"},
                )
        elif outra_parte:
            notify(
                outra_parte,
                tipo="contrato_assinado",
                titulo="Contrato aguardando sua assinatura",
                mensagem="A outra parte assinou o contrato de edição. Falta apenas a sua assinatura.",
                link=f"/contratos?contrato={cid}",
                payload={"contract_id": cid, "tipo": "edicao"},
            )
    except Exception:
        pass

    atualizado = sb.table("contracts_edicao").select("*").eq("id", cid).single().execute()
    return jsonify(atualizado.data)
