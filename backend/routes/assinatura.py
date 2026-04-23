"""Routes: /api/assinatura — Gerencia assinatura PRO (Stripe Subscriptions)."""
import os
from flask import Blueprint, request, jsonify, g, abort
from middleware.auth import require_auth
from db.supabase_client import get_supabase
from services.subscription import (
    criar_checkout_assinatura, cancelar_assinatura, PRO_PRICE_CENTS,
)
from services.migration_check import migration_applied
from app import limiter

assinatura_bp = Blueprint("assinatura", __name__)


def _perfil():
    sb = get_supabase()
    r = sb.table("perfis").select("*").eq("id", g.user.id).single().execute()
    if not r.data:
        abort(404, description="Perfil não encontrado.")
    return r.data


@assinatura_bp.route("/status", methods=["GET"])
@require_auth
def status():
    # Se a migração de assinatura ainda não foi rodada, retorna defaults
    # ao invés de quebrar a UI.
    if not migration_applied():
        return jsonify({
            "plano":             "STARTER",
            "status_assinatura": "inativa",
            "assinatura_inicio": None,
            "assinatura_fim":    None,
            "fee_pct":           20,
            "preco_pro_cents":   PRO_PRICE_CENTS,
            "migration_applied": False,
        }), 200

    p = _perfil()
    return jsonify({
        "plano":             p.get("plano", "STARTER"),
        "status_assinatura": p.get("status_assinatura", "inativa"),
        "assinatura_inicio": p.get("assinatura_inicio"),
        "assinatura_fim":    p.get("assinatura_fim"),
        "fee_pct":           15 if p.get("plano") == "PRO" else 20,
        "preco_pro_cents":   PRO_PRICE_CENTS,
        "migration_applied": True,
    }), 200


@assinatura_bp.route("/checkout", methods=["POST"])
@require_auth
@limiter.limit("20 per hour")
def checkout():
    # Proteção: não permite checkout se migração não rodou
    # (senão pagamento seria confirmado mas não poderia ser gravado)
    if not migration_applied():
        abort(503, description="Sistema de assinatura ainda não configurado. O administrador precisa rodar a migração do banco (backend/db/migration_assinatura.sql).")

    data = request.get_json(force=True, silent=True) or {}
    origin = (data.get("origin_url") or os.environ.get("FRONTEND_URL") or "").rstrip("/")
    if not origin:
        abort(422, description="origin_url obrigatório.")

    p = _perfil()
    try:
        out = criar_checkout_assinatura(p, origin)
    except ValueError as e:
        abort(422, description=str(e))
    except Exception as e:
        abort(500, description=f"Erro ao criar checkout: {e}")
    return jsonify(out), 200


@assinatura_bp.route("/cancelar", methods=["POST"])
@require_auth
@limiter.limit("10 per hour")
def cancelar():
    if not migration_applied():
        abort(503, description="Sistema de assinatura ainda não configurado.")
    p = _perfil()
    try:
        out = cancelar_assinatura(p)
    except ValueError as e:
        abort(422, description=str(e))
    except Exception as e:
        abort(500, description=f"Erro ao cancelar: {e}")
    return jsonify(out), 200


@assinatura_bp.route("/sincronizar", methods=["POST"])
@require_auth
@limiter.limit("10 per hour")
def sincronizar():
    """
    Sincroniza o estado da assinatura diretamente do Stripe.
    Útil quando o webhook falhou e o usuário ficou STARTER mesmo após pagar.
    Busca a última subscription ativa do customer e aplica no banco.
    """
    if not migration_applied():
        abort(503, description="Migração pendente.")
    import stripe
    from services.subscription import _ativar_pro, _get_or_create_customer
    stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")
    if not stripe.api_key:
        abort(500, description="Stripe não configurado.")

    p = _perfil()
    customer_id = p.get("stripe_customer_id")

    # Se não tem customer, procura pelo email
    if not customer_id and p.get("email"):
        try:
            search = stripe.Customer.list(email=p["email"], limit=1)
            if search.data:
                customer_id = search.data[0].id
                sb = get_supabase()
                sb.table("perfis").update({"stripe_customer_id": customer_id}).eq("id", p["id"]).execute()
        except Exception:
            pass

    if not customer_id:
        return jsonify({"encontrado": False, "motivo": "Nenhuma compra registrada no Stripe."}), 200

    try:
        subs = stripe.Subscription.list(customer=customer_id, status="all", limit=10)
    except Exception as e:
        abort(500, description=f"Erro ao consultar Stripe: {e}")

    # Prefere assinatura ativa; senão, a mais recente
    subs_list = list(subs.data or [])
    if not subs_list:
        return jsonify({"encontrado": False, "motivo": "Nenhuma assinatura encontrada no Stripe."}), 200

    active = next((s for s in subs_list if s.status in ("active", "trialing", "past_due")), None)
    sub = active or subs_list[0]

    # Garante metadata com perfil_id
    if not (sub.metadata or {}).get("perfil_id"):
        try:
            stripe.Subscription.modify(sub.id, metadata={"perfil_id": str(p["id"])})
        except Exception:
            pass

    _ativar_pro(str(p["id"]), sub if isinstance(sub, dict) else sub.to_dict())
    p2 = _perfil()
    return jsonify({
        "encontrado": True,
        "plano":             p2.get("plano"),
        "status_assinatura": p2.get("status_assinatura"),
        "assinatura_fim":    p2.get("assinatura_fim"),
    }), 200


@assinatura_bp.route("/confirmar/<session_id>", methods=["POST"])
@require_auth
@limiter.limit("30 per hour")
def confirmar_sessao(session_id):
    """
    Fallback do webhook — verifica a sessão do Stripe e ativa PRO se pago.
    Útil em ambientes onde o webhook não alcança o backend (ex.: localhost).
    """
    if not migration_applied():
        abort(503, description="Migração pendente.")
    import stripe
    from services.subscription import _ativar_pro, on_checkout_completed
    stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")

    if not stripe.api_key:
        abort(500, description="Stripe não configurado.")
    try:
        session = stripe.checkout.Session.retrieve(session_id, expand=["subscription"])
    except Exception as e:
        abort(404, description=f"Sessão não encontrada: {e}")

    # Valida que a sessão pertence a este usuário (metadata)
    meta = session.get("metadata") or {}
    if meta.get("perfil_id") and meta["perfil_id"] != str(g.user.id):
        abort(403, description="Sessão não pertence a este usuário.")

    if session.get("mode") != "subscription":
        abort(422, description="Sessão não é de assinatura.")

    if session.get("payment_status") != "paid":
        return jsonify({
            "ativado": False,
            "payment_status": session.get("payment_status"),
        }), 200

    # Pagamento confirmado — ativa PRO
    try:
        on_checkout_completed(session if isinstance(session, dict) else session.to_dict())
    except Exception as e:
        abort(500, description=f"Falha ao ativar PRO: {e}")

    p = _perfil()
    return jsonify({
        "ativado": True,
        "plano": p.get("plano"),
        "status_assinatura": p.get("status_assinatura"),
        "assinatura_fim": p.get("assinatura_fim"),
    }), 200
