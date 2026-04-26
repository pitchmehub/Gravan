"""
Rotas para Web Push (PWA).

  GET   /api/push/public-key         → devolve a VAPID public key (não-secreta)
  POST  /api/push/subscribe          → registra a assinatura do navegador
  POST  /api/push/unsubscribe        → remove assinatura por endpoint
  POST  /api/push/test               → envia push de teste para o usuário logado
"""
from flask import Blueprint, jsonify, request, g, abort

from middleware.auth import require_auth
from db.supabase_client import get_supabase
from services.push_service import vapid_public_key, send_push, is_configured

push_bp = Blueprint("push", __name__, url_prefix="/api/push")


@push_bp.get("/public-key")
def public_key():
    return jsonify({"public_key": vapid_public_key(), "enabled": is_configured()})


@push_bp.post("/subscribe")
@require_auth
def subscribe():
    data = request.get_json(silent=True) or {}
    endpoint = (data.get("endpoint") or "").strip()
    keys     = data.get("keys") or {}
    p256dh   = (keys.get("p256dh") or "").strip()
    auth_key = (keys.get("auth")   or "").strip()
    if not endpoint or not p256dh or not auth_key:
        abort(400, description="Assinatura push inválida")

    sb = get_supabase()
    payload = {
        "perfil_id":  g.user.id,
        "endpoint":   endpoint,
        "p256dh":     p256dh,
        "auth_key":   auth_key,
        "user_agent": request.headers.get("User-Agent", "")[:255],
    }

    # upsert por endpoint
    sb.table("push_subscriptions").upsert(payload, on_conflict="endpoint").execute()
    return jsonify({"ok": True})


@push_bp.post("/unsubscribe")
@require_auth
def unsubscribe():
    data = request.get_json(silent=True) or {}
    endpoint = (data.get("endpoint") or "").strip()
    if not endpoint:
        abort(400, description="Endpoint obrigatório")

    sb = get_supabase()
    sb.table("push_subscriptions").delete() \
      .eq("perfil_id", g.user.id).eq("endpoint", endpoint).execute()
    return jsonify({"ok": True})


@push_bp.post("/test")
@require_auth
def teste():
    enviados = send_push(
        g.user.id,
        title="Push funcionando 🎉",
        body="Notificações push da Gravan estão ativas neste dispositivo.",
        url="/dashboard",
        tag="teste",
    )
    return jsonify({"ok": True, "enviados": enviados})
