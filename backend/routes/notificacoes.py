"""Rotas REST para notificações do usuário logado."""
from flask import Blueprint, jsonify, g, request
from middleware.auth import require_auth
from db.supabase_client import get_supabase

notificacoes_bp = Blueprint("notificacoes", __name__)


def _user_id():
    # tenta os padrões mais comuns; ajustamos depois se nenhum servir
    if hasattr(g, "user") and getattr(g.user, "id", None):
        return g.user.id
    if hasattr(g, "user_id"):
        return g.user.id
    return None


@notificacoes_bp.route("/", methods=["GET"])
@require_auth
def listar():
    sb = get_supabase()
    try:
        limit  = min(50, max(1, int(request.args.get("limit", 20))))
        offset = max(0, int(request.args.get("offset", 0)))
    except ValueError:
        limit, offset = 20, 0
    only_unread = (request.args.get("nao_lidas") or "").lower() in ("1", "true", "yes")

    q = (sb.table("notificacoes")
         .select("*", count="exact")
         .eq("perfil_id", _user_id()))
    if only_unread:
        q = q.eq("lida", False)
    r = q.order("criada_em", desc=True).range(offset, offset + limit - 1).execute()

    items = r.data or []
    # compat: se o cliente NÃO pediu paginação, devolve só a lista (formato antigo)
    if "offset" not in request.args and "nao_lidas" not in request.args:
        return jsonify(items), 200

    return jsonify({
        "items":   items,
        "total":   r.count or 0,
        "offset":  offset,
        "limit":   limit,
        "has_more": (offset + len(items)) < (r.count or 0),
    }), 200


@notificacoes_bp.route("/<nid>", methods=["GET"])
@require_auth
def obter(nid):
    """Retorna uma única notificação do usuário logado (404 se não for dele)."""
    sb = get_supabase()
    r = (sb.table("notificacoes")
         .select("*")
         .eq("id", nid)
         .eq("perfil_id", _user_id())
         .limit(1)
         .execute())
    items = r.data or []
    if not items:
        return jsonify({"error": "not_found"}), 404
    return jsonify(items[0]), 200


@notificacoes_bp.route("/nao-lidas", methods=["GET"])
@require_auth
def contar_nao_lidas():
    sb = get_supabase()
    r = (sb.table("notificacoes")
         .select("id", count="exact")
         .eq("perfil_id", _user_id())
         .eq("lida", False)
         .execute())
    return jsonify({"total": r.count or 0}), 200


@notificacoes_bp.route("/<nid>/marcar-lida", methods=["PATCH"])
@require_auth
def marcar_lida(nid):
    sb = get_supabase()
    sb.table("notificacoes") \
      .update({"lida": True, "lida_em": "now()"}) \
      .eq("id", nid) \
      .eq("perfil_id", _user_id()) \
      .execute()
    return jsonify({"ok": True}), 200


@notificacoes_bp.route("/marcar-todas-lidas", methods=["PATCH"])
@require_auth
def marcar_todas():
    sb = get_supabase()
    sb.table("notificacoes") \
      .update({"lida": True, "lida_em": "now()"}) \
      .eq("perfil_id", _user_id()) \
      .eq("lida", False) \
      .execute()
    return jsonify({"ok": True}), 200


@notificacoes_bp.route("/<nid>/marcar-nao-lida", methods=["PATCH"])
@require_auth
def marcar_nao_lida(nid):
    sb = get_supabase()
    sb.table("notificacoes") \
      .update({"lida": False, "lida_em": None}) \
      .eq("id", nid) \
      .eq("perfil_id", _user_id()) \
      .execute()
    return jsonify({"ok": True}), 200


@notificacoes_bp.route("/<nid>", methods=["DELETE"])
@require_auth
def excluir(nid):
    sb = get_supabase()
    sb.table("notificacoes") \
      .delete() \
      .eq("id", nid) \
      .eq("perfil_id", _user_id()) \
      .execute()
    return jsonify({"ok": True}), 200