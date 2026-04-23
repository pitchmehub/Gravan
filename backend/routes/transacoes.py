"""
Routes: /api/transacoes
Apenas leitura. Criacao de transacoes agora e via /api/stripe/checkout.
"""
from flask import Blueprint, request, jsonify, g, abort
from middleware.auth import require_auth
from db.supabase_client import get_supabase

transacoes_bp = Blueprint("transacoes", __name__)


@transacoes_bp.route("/minhas", methods=["GET"])
@require_auth
def minhas_transacoes():
    """Historico de compras do interprete autenticado."""
    sb = get_supabase()
    resp = (
        sb.table("transacoes")
        .select("id, created_at, confirmed_at, status, metodo, valor_cents, obras(nome)")
        .eq("comprador_id", g.user.id)
        .order("created_at", desc=True)
        .limit(100)
        .execute()
    )
    return jsonify(resp.data or []), 200
