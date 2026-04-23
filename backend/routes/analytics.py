"""Routes: /api/analytics — Métricas de engajamento (apenas PRO + dono da obra)."""
from flask import Blueprint, jsonify, g, abort, request
from middleware.auth import require_auth
from middleware.plano import require_pro
from db.supabase_client import get_supabase
from services.migration_check import migration_applied
from utils.crypto import hash_ip
from app import limiter

analytics_bp = Blueprint("analytics", __name__)


@analytics_bp.route("/resumo", methods=["GET"])
@require_auth
@require_pro
def resumo_pro():
    """Agrega totais (plays, favoritos) de todas as obras do compositor PRO."""
    if not migration_applied():
        return jsonify({"total_plays": 0, "total_favoritos": 0, "obras": []}), 200
    sb = get_supabase()
    obras = sb.table("obras").select("id, nome").eq("titular_id", g.user.id).execute()
    ids = [o["id"] for o in (obras.data or [])]
    if not ids:
        return jsonify({"total_plays": 0, "total_favoritos": 0, "obras": []}), 200

    stats = sb.table("obra_analytics").select("obra_id, plays_count, favorites_count, last_played_at").in_("obra_id", ids).execute()
    mapa = {s["obra_id"]: s for s in (stats.data or [])}

    lista = []
    total_p = total_f = 0
    for o in obras.data:
        s = mapa.get(o["id"], {})
        p = int(s.get("plays_count") or 0)
        f = int(s.get("favorites_count") or 0)
        total_p += p; total_f += f
        lista.append({
            "obra_id":   o["id"],
            "nome":      o["nome"],
            "plays":     p,
            "favoritos": f,
            "last_played_at": s.get("last_played_at"),
        })

    lista.sort(key=lambda x: x["plays"] + x["favoritos"] * 3, reverse=True)
    return jsonify({
        "total_plays":     total_p,
        "total_favoritos": total_f,
        "obras":           lista,
    }), 200


@analytics_bp.route("/obra/<obra_id>", methods=["GET"])
@require_auth
@require_pro
def detalhe_obra(obra_id):
    """Métricas detalhadas de uma obra específica (só o titular)."""
    sb = get_supabase()
    o = sb.table("obras").select("titular_id, nome").eq("id", obra_id).single().execute()
    if not o.data:
        abort(404, description="Obra não encontrada.")
    if o.data["titular_id"] != g.user.id:
        abort(403, description="Apenas o titular pode ver as métricas desta obra.")

    stats = sb.table("obra_analytics").select("*").eq("obra_id", obra_id).limit(1).execute()
    s = (stats.data or [{}])[0]
    return jsonify({
        "obra_id":          obra_id,
        "nome":             o.data["nome"],
        "plays":            int(s.get("plays_count") or 0),
        "favoritos":        int(s.get("favorites_count") or 0),
        "last_played_at":   s.get("last_played_at"),
    }), 200


# ─────────────────────────────────────────────────────────────────
# Endpoint público de registro de play (não exige PRO nem auth)
# ─────────────────────────────────────────────────────────────────
@analytics_bp.route("/play/<obra_id>", methods=["POST"])
@limiter.limit("120 per hour")
def registrar_play(obra_id):
    """Registra um play para alimentar analytics. Público, rate-limited por IP."""
    if not migration_applied():
        return jsonify({"ok": True, "skipped": True}), 200
    sb = get_supabase()
    o = sb.table("obras").select("id").eq("id", obra_id).limit(1).execute()
    if not o.data:
        abort(404, description="Obra não encontrada.")

    # Identifica usuário se houver JWT
    perfil_id = None
    try:
        from middleware.auth import extract_user_if_present
        u = extract_user_if_present()
        perfil_id = u.id if u else None
    except Exception:
        perfil_id = None

    try:
        sb.table("play_events").insert({
            "obra_id":   obra_id,
            "perfil_id": perfil_id,
            "ip_hash":   hash_ip(request.remote_addr or ""),
        }).execute()
    except Exception:
        pass
    return jsonify({"ok": True}), 200
