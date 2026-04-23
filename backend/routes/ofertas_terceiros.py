"""
Routes: /api/ofertas-licenciamento

Endpoints:
- POST   /                              cria uma oferta (intérprete)
- GET    /minhas                        ofertas do usuário (comprador)
- GET    /editora                       ofertas para a editora logada
- GET    /<id>                          detalhe (comprador / editora / admin)
- GET    /por-token/<token>             dados públicos da oferta para landing
- POST   /<id>/cron-tick                manualmente dispara lembretes/expiração (admin)
"""
from flask import Blueprint, request, jsonify, g, abort
from middleware.auth import require_auth
from db.supabase_client import get_supabase
from services.ofertas_terceiros import (
    criar_oferta,
    processar_lembretes_e_expiracoes,
)
from utils.business_hours import business_hours_remaining
from datetime import datetime

ofertas_lic_bp = Blueprint("ofertas_lic", __name__, url_prefix="/api/ofertas-licenciamento")


def _perfil():
    sb = get_supabase()
    return (sb.table("perfis").select("*").eq("id", g.user.id).single().execute().data) or {}


@ofertas_lic_bp.post("")
@ofertas_lic_bp.post("/")
@require_auth
def criar():
    data = request.get_json(silent=True) or {}
    obra_id = data.get("obra_id")
    if not obra_id:
        abort(422, description="obra_id obrigatório.")
    perfil = _perfil()
    if not perfil:
        abort(404, description="Perfil não encontrado.")
    if not perfil.get("cadastro_completo"):
        abort(422, description="Complete seu cadastro antes de fazer uma oferta.")
    try:
        out = criar_oferta(
            obra_id=obra_id,
            comprador_id=g.user.id,
            metodo=data.get("metodo", "credito"),
        )
    except ValueError as e:
        abort(422, description=str(e))
    except RuntimeError as e:
        abort(500, description=str(e))
    return jsonify(out), 201


def _enriquecer(of: dict) -> dict:
    """Anexa horas restantes (úteis), obra, comprador e contract_id."""
    sb = get_supabase()
    obra = sb.table("obras").select("id, nome, preco_cents, audio_path, titular_id").eq(
        "id", of["obra_id"]
    ).single().execute().data or {}
    of["obra"] = obra

    if of.get("comprador_id"):
        comp = sb.table("perfis").select("id, nome").eq("id", of["comprador_id"]).single().execute().data
        of["comprador"] = comp
    else:
        of["comprador"] = None

    contr = sb.table("contracts").select("id").eq("oferta_id", of["id"]).limit(1).execute().data or []
    of["contract_id"] = contr[0]["id"] if contr else None

    try:
        deadline = datetime.fromisoformat(of["deadline_at"].replace("Z", "+00:00"))
        of["horas_uteis_restantes"] = business_hours_remaining(deadline)
    except Exception:
        of["horas_uteis_restantes"] = None
    return of


@ofertas_lic_bp.get("/minhas")
@require_auth
def minhas():
    sb = get_supabase()
    rows = sb.table("ofertas_licenciamento").select("*").eq(
        "comprador_id", g.user.id
    ).order("created_at", desc=True).execute().data or []
    return jsonify([_enriquecer(r) for r in rows])


@ofertas_lic_bp.get("/editora")
@require_auth
def para_editora():
    perfil = _perfil()
    if perfil.get("role") not in ("publisher", "administrador"):
        abort(403, description="Apenas editoras.")

    sb = get_supabase()
    # Vinculadas + pendentes pelo email
    vinc = sb.table("ofertas_licenciamento").select("*").eq(
        "editora_terceira_id", g.user.id
    ).execute().data or []
    pend = []
    if perfil.get("email"):
        pend = sb.table("ofertas_licenciamento").select("*").eq(
            "editora_terceira_email", perfil["email"].lower()
        ).is_("editora_terceira_id", "null").in_(
            "status", ["aguardando_editora"]
        ).execute().data or []

    seen = set()
    out = []
    for r in vinc + pend:
        if r["id"] in seen: continue
        seen.add(r["id"])
        out.append(_enriquecer(r))
    out.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return jsonify(out)


@ofertas_lic_bp.get("/<oferta_id>")
@require_auth
def detalhe(oferta_id):
    sb = get_supabase()
    of = sb.table("ofertas_licenciamento").select("*").eq("id", oferta_id).single().execute().data
    if not of:
        abort(404, description="Oferta não encontrada.")
    perfil = _perfil()
    if (g.user.id != of["comprador_id"]
        and g.user.id != of.get("editora_terceira_id")
        and perfil.get("role") != "administrador"):
        abort(403, description="Acesso negado.")
    return jsonify(_enriquecer(of))


@ofertas_lic_bp.get("/por-token/<token>")
def por_token(token):
    """Endpoint PÚBLICO usado na landing de cadastro da editora terceira."""
    sb = get_supabase()
    rows = sb.table("ofertas_licenciamento").select(
        "id, obra_id, comprador_id, valor_cents, mensagem, status, deadline_at,"
        " editora_terceira_nome, editora_terceira_email"
    ).eq("registration_token", token).limit(1).execute().data or []
    if not rows:
        abort(404, description="Link inválido ou expirado.")
    of = rows[0]

    if of["status"] not in ("aguardando_editora",):
        abort(409, description=f"Esta oferta já foi {of['status']} e não pode mais ser aceita.")

    obra = sb.table("obras").select("id, nome, titular_id").eq("id", of["obra_id"]).single().execute().data or {}
    titular = (sb.table("perfis").select("id, nome").eq("id", obra.get("titular_id")).single().execute().data
               if obra.get("titular_id") else None)
    comprador = (sb.table("perfis").select("id, nome").eq("id", of["comprador_id"]).single().execute().data
                 if of.get("comprador_id") else None)

    out = {
        "id": of["id"],
        "valor_cents": of["valor_cents"],
        "mensagem": of.get("mensagem"),
        "status": of["status"],
        "deadline_at": of["deadline_at"],
        "editora_terceira_nome":  of.get("editora_terceira_nome"),
        "editora_terceira_email": of.get("editora_terceira_email"),
        "obra": {"id": obra.get("id"), "nome": obra.get("nome")},
        "compositor": titular,
        "comprador":  comprador,
    }
    try:
        deadline = datetime.fromisoformat(of["deadline_at"].replace("Z", "+00:00"))
        out["horas_uteis_restantes"] = business_hours_remaining(deadline)
    except Exception:
        out["horas_uteis_restantes"] = None
    return jsonify(out)


@ofertas_lic_bp.post("/cron-tick")
@require_auth
def cron_tick():
    perfil = _perfil()
    if perfil.get("role") != "administrador":
        abort(403, description="Somente administrador.")
    return jsonify(processar_lembretes_e_expiracoes())
