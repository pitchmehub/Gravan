"""
Service de assinatura PRO — integra com Stripe Subscriptions.

Fluxo:
  1. Usuário cria checkout (mode=subscription) → redirecionado ao Stripe
  2. Stripe confirma pagamento → webhook checkout.session.completed
  3. Webhook ativa PRO no banco (plano, status_assinatura, datas, subscription_id)
  4. Renovação automática → invoice.paid apenas atualiza assinatura_fim
  5. Cancelamento (user solicita) → cancel_at_period_end=true; PRO até fim do ciclo
  6. Ciclo termina sem renovação → customer.subscription.deleted → volta a STARTER
"""
import os
from datetime import datetime, timezone
from typing import Optional

import stripe
from db.supabase_client import get_supabase


PRO_PRICE_CENTS  = 2990  # R$ 29,90
PRO_CURRENCY     = "brl"
PRO_PRODUCT_NAME = "Pitch.me PRO"


def _ensure_stripe_key():
    if not stripe.api_key:
        stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")
    if not stripe.api_key:
        raise RuntimeError("STRIPE_SECRET_KEY ausente no .env")


def get_or_create_pro_price() -> str:
    """
    Retorna o Stripe Price ID do plano PRO. Se não existir, cria sob demanda.
    Cacheia em env var PITCHME_PRO_PRICE_ID para requests futuros.
    """
    _ensure_stripe_key()
    cached = os.environ.get("PITCHME_PRO_PRICE_ID")
    if cached:
        return cached

    # Procura um price recorrente já existente com esse nickname
    prices = stripe.Price.list(active=True, limit=100, lookup_keys=["pitchme_pro_monthly"])
    if prices.data:
        price_id = prices.data[0].id
        os.environ["PITCHME_PRO_PRICE_ID"] = price_id
        return price_id

    # Cria produto + price
    product = stripe.Product.create(name=PRO_PRODUCT_NAME)
    price = stripe.Price.create(
        product=product.id,
        unit_amount=PRO_PRICE_CENTS,
        currency=PRO_CURRENCY,
        recurring={"interval": "month"},
        lookup_key="pitchme_pro_monthly",
        nickname="Pitch.me PRO — Mensal",
    )
    os.environ["PITCHME_PRO_PRICE_ID"] = price.id
    return price.id


def _get_or_create_customer(perfil: dict) -> str:
    """Retorna o stripe_customer_id do usuário, criando se não existir."""
    _ensure_stripe_key()
    existing = perfil.get("stripe_customer_id")
    if existing:
        return existing

    customer = stripe.Customer.create(
        email=perfil.get("email"),
        name=perfil.get("nome_completo") or perfil.get("nome") or "",
        metadata={"perfil_id": str(perfil["id"])},
    )
    sb = get_supabase()
    sb.table("perfis").update({"stripe_customer_id": customer.id}).eq("id", perfil["id"]).execute()
    return customer.id


def criar_checkout_assinatura(perfil: dict, origin_url: str) -> dict:
    """Cria a Stripe Checkout Session em modo subscription."""
    _ensure_stripe_key()
    if perfil.get("plano") == "PRO" and perfil.get("status_assinatura") == "ativa":
        raise ValueError("Você já tem uma assinatura PRO ativa.")

    price_id   = get_or_create_pro_price()
    customer_id = _get_or_create_customer(perfil)

    session = stripe.checkout.Session.create(
        mode="subscription",
        customer=customer_id,
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=f"{origin_url}/assinatura/sucesso?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{origin_url}/planos?canceled=1",
        allow_promotion_codes=True,
        metadata={"perfil_id": str(perfil["id"]), "plano": "PRO"},
        subscription_data={
            "metadata": {"perfil_id": str(perfil["id"])},
        },
    )
    return {"checkout_url": session.url, "session_id": session.id}


def cancelar_assinatura(perfil: dict) -> dict:
    """Cancela a assinatura no fim do ciclo atual. PRO continua até a data final."""
    _ensure_stripe_key()
    sub_id = perfil.get("stripe_subscription_id")
    if not sub_id:
        raise ValueError("Você não possui assinatura ativa.")

    sub = stripe.Subscription.modify(sub_id, cancel_at_period_end=True)
    sb = get_supabase()
    sb.table("perfis").update({
        "status_assinatura": "cancelada",
        "assinatura_fim":    _ts(sub.get("current_period_end")),
    }).eq("id", perfil["id"]).execute()

    return {
        "status":  "cancelada",
        "ativa_ate": _ts(sub.get("current_period_end")),
    }


def _ts(epoch: Optional[int]) -> Optional[str]:
    if not epoch:
        return None
    return datetime.fromtimestamp(int(epoch), tz=timezone.utc).isoformat()


# ─────────────────────────────────────────────────────────────────
# Handlers de webhook (chamados pelo stripe_routes.py)
# ─────────────────────────────────────────────────────────────────

def on_checkout_completed(session_obj: dict):
    """checkout.session.completed em mode=subscription → ativa PRO."""
    if session_obj.get("mode") != "subscription":
        return  # checkout de one-time purchase (licença) — ignora aqui

    perfil_id = (session_obj.get("metadata") or {}).get("perfil_id")
    sub_id    = session_obj.get("subscription")
    if not perfil_id or not sub_id:
        return

    _ensure_stripe_key()
    sub = stripe.Subscription.retrieve(sub_id)
    _ativar_pro(perfil_id, sub)


def on_subscription_updated(sub_obj: dict):
    """customer.subscription.updated → sincroniza datas/status."""
    perfil_id = (sub_obj.get("metadata") or {}).get("perfil_id")
    if not perfil_id:
        return
    _ativar_pro(perfil_id, sub_obj)


def on_subscription_deleted(sub_obj: dict):
    """customer.subscription.deleted → volta pra STARTER."""
    perfil_id = (sub_obj.get("metadata") or {}).get("perfil_id")
    if not perfil_id:
        return
    sb = get_supabase()
    sb.table("perfis").update({
        "plano":             "STARTER",
        "status_assinatura": "inativa",
        "assinatura_fim":    _ts(sub_obj.get("canceled_at") or sub_obj.get("ended_at")),
        "stripe_subscription_id": None,
    }).eq("id", perfil_id).execute()


def on_invoice_payment_failed(invoice_obj: dict):
    """Cobrança falhou — marca past_due mas não remove PRO imediatamente."""
    sub_id = invoice_obj.get("subscription")
    if not sub_id:
        return
    sb = get_supabase()
    sb.table("perfis").update({"status_assinatura": "past_due"}) \
      .eq("stripe_subscription_id", sub_id).execute()


def _ativar_pro(perfil_id: str, sub: dict):
    """Atualiza a tabela perfis com base na assinatura Stripe."""
    status = sub.get("status")  # active, past_due, canceled, incomplete, etc.
    cancel_at_end = bool(sub.get("cancel_at_period_end"))

    if status in ("active", "trialing"):
        novo_status = "cancelada" if cancel_at_end else "ativa"
        plano = "PRO"
    elif status == "past_due":
        novo_status, plano = "past_due", "PRO"
    else:
        # incomplete, canceled, unpaid, etc. — trata como STARTER
        novo_status, plano = "inativa", "STARTER"

    sb = get_supabase()
    sb.table("perfis").update({
        "plano":                 plano,
        "status_assinatura":     novo_status,
        "assinatura_inicio":     _ts(sub.get("start_date") or sub.get("current_period_start")),
        "assinatura_fim":        _ts(sub.get("current_period_end")),
        "stripe_subscription_id": sub.get("id"),
    }).eq("id", perfil_id).execute()
