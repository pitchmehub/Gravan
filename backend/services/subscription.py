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


PRO_PRICE_CENTS  = 4990  # R$ 49,90
PRO_CURRENCY     = "brl"
PRO_PRODUCT_NAME = "Gravan PRO"
PRO_LOOKUP_KEY   = "gravan_pro_monthly_4990"  # nova lookup_key p/ refletir o preço atual


def _ensure_stripe_key():
    if not stripe.api_key:
        stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")
    if not stripe.api_key:
        raise RuntimeError("STRIPE_SECRET_KEY ausente no .env")


def get_or_create_pro_price() -> str:
    """
    Retorna o Stripe Price ID do plano PRO. Se não existir, cria sob demanda.
    Cacheia em env var GRAVAN_PRO_PRICE_ID para requests futuros.
    """
    _ensure_stripe_key()
    cached = os.environ.get("GRAVAN_PRO_PRICE_ID")
    if cached:
        return cached

    # Procura um price recorrente já existente com a lookup_key atual
    prices = stripe.Price.list(active=True, limit=100, lookup_keys=[PRO_LOOKUP_KEY])
    if prices.data:
        price_id = prices.data[0].id
        os.environ["GRAVAN_PRO_PRICE_ID"] = price_id
        return price_id

    # Cria produto + price com o valor atual (R$ 49,90/mês)
    product = stripe.Product.create(name=PRO_PRODUCT_NAME)
    price = stripe.Price.create(
        product=product.id,
        unit_amount=PRO_PRICE_CENTS,
        currency=PRO_CURRENCY,
        recurring={"interval": "month"},
        lookup_key=PRO_LOOKUP_KEY,
        nickname=f"Gravan PRO — Mensal R$ {PRO_PRICE_CENTS/100:.2f}".replace(".", ","),
    )
    os.environ["GRAVAN_PRO_PRICE_ID"] = price.id
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
    sb = get_supabase()
    if not perfil_id:
        # fallback: localiza pelo stripe_subscription_id
        sub_id = sub_obj.get("id")
        if sub_id:
            row = sb.table("perfis").select("id").eq(
                "stripe_subscription_id", sub_id
            ).limit(1).execute()
            if row.data:
                perfil_id = row.data[0]["id"]
    if not perfil_id:
        return

    update = {
        "plano":             "STARTER",
        "status_assinatura": "inativa",
        "assinatura_fim":    _ts(sub_obj.get("canceled_at") or sub_obj.get("ended_at")),
        "stripe_subscription_id": None,
    }
    # tenta limpar past_due_desde (coluna pode não existir em DBs antigos)
    try:
        sb.table("perfis").update({**update, "past_due_desde": None}) \
          .eq("id", perfil_id).execute()
    except Exception:
        sb.table("perfis").update(update).eq("id", perfil_id).execute()

    # Notifica o usuário do downgrade
    try:
        from services.notificacoes import notify
        notify(
            perfil_id=perfil_id,
            tipo="assinatura",
            titulo="Sua assinatura PRO foi encerrada",
            mensagem=(
                "Sua conta voltou para o plano STARTER. As condições do plano "
                "STARTER (taxa de plataforma de 20%) já valem para suas próximas "
                "vendas. Você pode reativar o PRO quando quiser na página de Planos."
            ),
            link="/planos",
        )
    except Exception:
        pass


def on_invoice_payment_failed(invoice_obj: dict):
    """
    Cobrança falhou — marca past_due e carimba `past_due_desde` (1ª falha).
    O downgrade automático para STARTER acontece após 7 dias contados desse
    carimbo, via `expirar_assinaturas_em_atraso()` (rodada pelo watchdog).
    """
    sub_id = invoice_obj.get("subscription")
    if not sub_id:
        return
    sb = get_supabase()
    row = sb.table("perfis").select("id, past_due_desde").eq(
        "stripe_subscription_id", sub_id
    ).limit(1).execute()
    if not row.data:
        return
    perf = row.data[0]

    update = {"status_assinatura": "past_due"}
    if not perf.get("past_due_desde"):
        update["past_due_desde"] = datetime.now(timezone.utc).isoformat()

    try:
        sb.table("perfis").update(update).eq("id", perf["id"]).execute()
    except Exception:
        # coluna past_due_desde inexistente: aplica só o status
        sb.table("perfis").update({"status_assinatura": "past_due"}) \
          .eq("id", perf["id"]).execute()

    # Notifica o usuário sobre a falha
    try:
        from services.notificacoes import notify
        notify(
            perfil_id=perf["id"],
            tipo="assinatura",
            titulo="Falha na cobrança da sua assinatura PRO",
            mensagem=(
                "Não conseguimos cobrar sua assinatura PRO. Vamos tentar novamente "
                "nos próximos dias. Atualize seu cartão na página de Planos para "
                "evitar a perda do plano PRO em até 7 dias."
            ),
            link="/planos",
        )
    except Exception:
        pass


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
    update = {
        "plano":                 plano,
        "status_assinatura":     novo_status,
        "assinatura_inicio":     _ts(sub.get("start_date") or sub.get("current_period_start")),
        "assinatura_fim":        _ts(sub.get("current_period_end")),
        "stripe_subscription_id": sub.get("id"),
    }
    # Limpa o relógio de past_due quando a assinatura volta a ficar saudável
    if novo_status in ("ativa", "cancelada"):
        try:
            sb.table("perfis").update({**update, "past_due_desde": None}) \
              .eq("id", perfil_id).execute()
            return
        except Exception:
            pass
    sb.table("perfis").update(update).eq("id", perfil_id).execute()


# ─────────────────────────────────────────────────────────────────
# Dunning: força cancelamento após 7 dias de past_due
# ─────────────────────────────────────────────────────────────────

DUNNING_GRACE_DAYS = 7  # dias após 1ª falha de cobrança até cancelar PRO


def expirar_assinaturas_em_atraso() -> dict:
    """
    Rotina periódica (chamada pelo watchdog).
    Para cada perfil com `status_assinatura='past_due'` há mais de
    `DUNNING_GRACE_DAYS` dias, cancela a assinatura no Stripe.
    Isso dispara `customer.subscription.deleted` que volta o perfil
    para STARTER pelo handler já existente.
    Idempotente e seguro de chamar repetidamente.
    """
    _ensure_stripe_key()
    sb = get_supabase()
    out = {"verificadas": 0, "canceladas": 0, "erros": 0}

    try:
        rows = sb.table("perfis").select(
            "id, stripe_subscription_id, past_due_desde"
        ).eq("status_assinatura", "past_due") \
         .not_.is_("past_due_desde", "null").execute().data or []
    except Exception:
        # coluna past_due_desde inexistente; nada a fazer ainda.
        return out

    cutoff = datetime.now(timezone.utc) - _td(days=DUNNING_GRACE_DAYS)

    for r in rows:
        out["verificadas"] += 1
        sub_id = r.get("stripe_subscription_id")
        try:
            past_dt = datetime.fromisoformat(
                r["past_due_desde"].replace("Z", "+00:00")
            )
        except Exception:
            continue

        if past_dt > cutoff:
            continue  # ainda dentro da janela de tolerância

        if not sub_id:
            # já não tem subscription Stripe associada — só rebaixa direto.
            try:
                sb.table("perfis").update({
                    "plano":             "STARTER",
                    "status_assinatura": "inativa",
                    "past_due_desde":    None,
                }).eq("id", r["id"]).execute()
                out["canceladas"] += 1
            except Exception:
                out["erros"] += 1
            continue

        try:
            stripe.Subscription.cancel(sub_id, invoice_now=False, prorate=False)
            out["canceladas"] += 1
        except stripe.StripeError as e:
            msg = str(e).lower()
            if "no such subscription" in msg or "resource_missing" in msg:
                # Sub já não existe no Stripe — limpa local
                try:
                    sb.table("perfis").update({
                        "plano":             "STARTER",
                        "status_assinatura": "inativa",
                        "stripe_subscription_id": None,
                        "past_due_desde":    None,
                    }).eq("id", r["id"]).execute()
                    out["canceladas"] += 1
                except Exception:
                    out["erros"] += 1
            else:
                out["erros"] += 1
        except Exception:
            out["erros"] += 1

    return out


def _td(**kw):
    from datetime import timedelta
    return timedelta(**kw)
