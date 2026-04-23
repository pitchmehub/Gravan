"""Routes: /api/favoritos — Biblioteca pessoal de obras curtidas (todos os planos)."""
from flask import Blueprint, jsonify, g, abort
from middleware.auth import require_auth
from db.supabase_client import get_supabase
from services.migration_check import migration_applied
from app import limiter

favoritos_bp = Blueprint("favoritos", __name__)


@favoritos_bp.route("", methods=["GET"])
@favoritos_bp.route("/", methods=["GET"])
@require_auth
def listar():
    """Lista as obras favoritadas do usuário (biblioteca pessoal)."""
    if not migration_applied():
        return jsonify([]), 200
    sb = get_supabase()
    r = (
        sb.table("favoritos")
          .select("id, created_at, obras(id, nome, genero, preco_cents, titular_id, status, perfis(nome, nivel))")
          .eq("perfil_id", g.user.id)
          .order("created_at", desc=True)
          .execute()
    )
    return jsonify(r.data or []), 200


@favoritos_bp.route("/<obra_id>", methods=["POST"])
@require_auth
@limiter.limit("120 per hour")
def favoritar(obra_id):
    if not migration_applied():
        abort(503, description="Sistema de favoritos ainda não configurado. Rode a migração do banco (migration_assinatura.sql).")
    sb = get_supabase()
    # Garante que a obra existe
    o = sb.table("obras").select("id").eq("id", obra_id).single().execute()
    if not o.data:
        abort(404, description="Obra não encontrada.")
    try:
        sb.table("favoritos").insert({
            "perfil_id": g.user.id,
            "obra_id":   obra_id,
        }).execute()
    except Exception:
        # Unique violation = já favoritou; não é erro
        pass
    return jsonify({"ok": True, "favoritada": True}), 200


@favoritos_bp.route("/<obra_id>", methods=["DELETE"])
@require_auth
@limiter.limit("120 per hour")
def desfavoritar(obra_id):
    if not migration_applied():
        abort(503, description="Sistema de favoritos ainda não configurado.")
    sb = get_supabase()
    sb.table("favoritos").delete() \
      .eq("perfil_id", g.user.id).eq("obra_id", obra_id).execute()
    return jsonify({"ok": True, "favoritada": False}), 200


@favoritos_bp.route("/status/<obra_id>", methods=["GET"])
@require_auth
def status_obra(obra_id):
    """Retorna se a obra está favoritada pelo usuário atual."""
    if not migration_applied():
        return jsonify({"favoritada": False, "available": False}), 200
    sb = get_supabase()
    r = sb.table("favoritos").select("id") \
        .eq("perfil_id", g.user.id).eq("obra_id", obra_id).limit(1).execute()
    return jsonify({"favoritada": bool(r.data), "available": True}), 200
