"""
Routes: /api/stripe — Stripe Checkout integration

CORREÇÕES DE VULNERABILIDADES:
- #6 (ALTA): Webhook validation melhorada
- #14 (MÉDIA): Audit logging de transações
"""
import os
import stripe
import json
import logging
from flask import Blueprint, request, jsonify, g, abort
from middleware.auth import require_auth
from db.supabase_client import get_supabase
from services.finance import calcular_split
from utils.audit import AuditLogger
from app import limiter

logger = logging.getLogger('gravan.stripe')

stripe_bp = Blueprint("stripe", __name__)
stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")
WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
FRONTEND_URL   = os.environ.get("FRONTEND_URL", "http://localhost:5173")

# Métodos Gravan -> Stripe (PIX exige ativação no Stripe BR; usamos card por padrão)
METODO_TO_STRIPE = {
    "pix":     ["card"],   # fallback: card (PIX precisa ativação manual no painel Stripe)
    "credito": ["card"],
    "debito":  ["card"],
    "boleto":  ["boleto"],
}


@stripe_bp.route("/checkout", methods=["POST"])
@require_auth
@limiter.limit("20 per hour")
def criar_checkout():
    if not stripe.api_key:
        abort(500, description="Stripe não configurado: STRIPE_SECRET_KEY ausente no .env")

    data = request.get_json(force=True, silent=True) or {}
    obra_id = data.get("obra_id")
    metodo  = data.get("metodo", "credito")
    concordou_contrato = bool(data.get("concordo_contrato", True))  # default True p/ backcompat

    # Validacao: comprador precisa ter cadastro completo
    sb_check = get_supabase()
    perfil_check = sb_check.table("perfis").select("cadastro_completo, role").eq("id", g.user.id).single().execute()
    if not perfil_check.data:
        abort(404, description="Perfil nao encontrado.")
    if not perfil_check.data.get("cadastro_completo"):
        abort(422, description="Complete seu cadastro (CPF, RG, endereco) antes de comprar.")
    if not concordou_contrato:
        abort(422, description="Marque a caixa de concordância com o contrato antes de prosseguir.")

    # Proteção anti-auto-compra: titular não pode comprar sua propria obra
    obra_check = sb_check.table("obras").select("titular_id").eq("id", obra_id).single().execute()
    if obra_check.data and obra_check.data.get("titular_id") == g.user.id:
        abort(422, description="Voce nao pode comprar uma obra de sua propria autoria.")

    if not obra_id:
        abort(422, description="obra_id obrigatório.")
    if metodo not in METODO_TO_STRIPE:
        abort(422, description=f"Método inválido: {metodo}")

    sb = get_supabase()

    # Busca a obra
    obra_resp = (
        sb.table("obras")
        .select("id, nome, preco_cents, status, titular_id")
        .eq("id", obra_id)
        .single()
        .execute()
    )
    if not obra_resp.data:
        abort(404, description="Obra não encontrada.")
    obra = obra_resp.data
    if obra.get("status") != "publicada":
        abort(422, description="Obra não está publicada.")
    if not obra.get("preco_cents") or obra["preco_cents"] < 100:
        abort(422, description="Obra com preço inválido.")

    # Nome e plano do compositor titular (fee depende do plano)
    try:
        titular = sb.table("perfis").select("nome, plano, status_assinatura").eq("id", obra["titular_id"]).single().execute()
        t_data = titular.data or {}
    except Exception:
        # Coluna `plano` pode não existir ainda (migração pendente). Usa defaults.
        titular = sb.table("perfis").select("nome").eq("id", obra["titular_id"]).single().execute()
        t_data = {**(titular.data or {}), "plano": "STARTER", "status_assinatura": "inativa"}
    titular_nome  = t_data.get("nome", "Gravan")
    plano_titular = t_data.get("plano", "STARTER")
    status_ass    = t_data.get("status_assinatura", "inativa")
    # PRO efetivo apenas com assinatura em dia
    if plano_titular == "PRO" and status_ass not in ("ativa", "cancelada", "past_due"):
        plano_titular = "STARTER"

    # Coautorias para split
    coaut = sb.table("coautorias").select("perfil_id, share_pct").eq("obra_id", obra_id).execute()
    coautorias = coaut.data or []
    if not coautorias:
        # Caso a obra não tenha coautoria registrada, cria automática 100% pro titular
        coautorias = [{"perfil_id": obra["titular_id"], "share_pct": 100}]

    try:
        split = calcular_split(obra["preco_cents"], coautorias, plano_titular=plano_titular)
    except ValueError as e:
        abort(422, description=str(e))

    # Cria a sessão Stripe
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=METODO_TO_STRIPE[metodo],
            mode="payment",
            line_items=[{
                "price_data": {
                    "currency": "brl",
                    "product_data": {
                        "name": f"Licença: {obra['nome']}",
                        "description": f"Composição musical de {titular_nome}",
                    },
                    "unit_amount": obra["preco_cents"],
                },
                "quantity": 1,
            }],
            customer_email=g.user.email,
            success_url=f"{FRONTEND_URL}/pagamento/sucesso?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{FRONTEND_URL}/pagamento/cancelado?session_id={{CHECKOUT_SESSION_ID}}",
            metadata={
                "obra_id":      obra_id,
                "comprador_id": g.user.id,
                "metodo":       metodo,
            },
        )
    except stripe.error.StripeError as e:
        msg = e.user_message or str(e)
        abort(500, description=f"Erro Stripe: {msg}")
    except Exception as e:
        abort(500, description=f"Erro ao criar checkout: {str(e)}")

    # Salva transação como pendente
    from utils.crypto import hash_ip
    from datetime import datetime, timezone
    try:
        sb.table("transacoes").insert({
            "obra_id":           obra_id,
            "comprador_id":      g.user.id,
            "valor_cents":       split.valor_cents,
            "plataforma_cents":  split.plataforma_cents,
            "liquido_cents":     split.liquido_cents,
            "metodo":            metodo,
            "status":            "pendente",
            "stripe_session_id": session.id,
            "stripe_url":        session.url,
            "metadata":          {
                "contrato_aceito": True,
                "aceite_ip_hash":  hash_ip(request.remote_addr or ""),
                "aceite_at":       datetime.now(timezone.utc).isoformat(),
                "aceite_user_agent": (request.headers.get("User-Agent") or "")[:200],
            },
        }).execute()
    except Exception as e:
        # Se a inserção falhar (ex.: coluna metadata não existe), tenta sem
        try:
            sb.table("transacoes").insert({
                "obra_id":           obra_id,
                "comprador_id":      g.user.id,
                "valor_cents":       split.valor_cents,
                "plataforma_cents":  split.plataforma_cents,
                "liquido_cents":     split.liquido_cents,
                "metodo":            metodo,
                "status":            "pendente",
                "stripe_session_id": session.id,
                "stripe_url":        session.url,
            }).execute()
        except Exception as e2:
            print(f"[WARN] Falha ao salvar transação: {e2}")

    return jsonify({
        "checkout_url": session.url,
        "session_id":   session.id,
    }), 200


@stripe_bp.route("/webhook", methods=["POST"])
def webhook():
    """
    Webhook do Stripe para confirmar pagamentos.
    
    CORREÇÃO VULNERABILIDADE #6 (ALTA): Validação melhorada de webhook.
    - SEMPRE exige WEBHOOK_SECRET em produção
    - Em dev, valida origem e exige localhost
    """
    payload   = request.data
    signature = request.headers.get("Stripe-Signature", "")
    
    # CORREÇÃO #6 (ALTA): Webhook validation melhorada
    is_dev = os.environ.get("FLASK_ENV", "development") == "development"
    is_prod = not is_dev

    try:
        # Em PRODUÇÃO: SEMPRE exige webhook secret
        if is_prod and not WEBHOOK_SECRET:
            logger.error("PRODUÇÃO sem STRIPE_WEBHOOK_SECRET configurado!")
            abort(500, description="Webhook não configurado corretamente.")
        
        if WEBHOOK_SECRET:
            # Validação completa com assinatura HMAC
            event = stripe.Webhook.construct_event(payload, signature, WEBHOOK_SECRET)
            event_type = event["type"]
            obj = event["data"]["object"]
            logger.info(f"Webhook validado: {event_type}")
            
        elif is_dev:
            # Dev sem secret: valida origem local APENAS
            if request.remote_addr not in ("127.0.0.1", "::1", "localhost"):
                logger.warning(f"Webhook de origem não-local rejeitado: {request.remote_addr}")
                abort(403, description="Webhook só aceito do localhost em dev.")
            
            event = json.loads(payload)
            event_type = event.get("type", "")
            obj = event.get("data", {}).get("object", {})
            logger.warning(f"Webhook DEV sem validação HMAC: {event_type}")
        else:
            abort(500, description="Configuração de webhook inválida.")
            
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Assinatura inválida: {e}")
        abort(400, description="Assinatura inválida do webhook.")
    except json.JSONDecodeError:
        logger.error("Payload JSON inválido")
        abort(400, description="Payload inválido.")
    except Exception as e:
        logger.error(f"Erro ao processar webhook: {e}")
        abort(400, description="Erro ao processar webhook.")

    sb = get_supabase()

    # Processa eventos
    if event_type == "checkout.session.completed":
        # Pode ser: licença one-time (mode=payment), assinatura PRO (mode=subscription)
        # ou OFERTA DE LICENCIAMENTO PARA EDITORA TERCEIRA (manual capture).
        meta = (obj.get("metadata") if isinstance(obj, dict) else getattr(obj, "metadata", {})) or {}
        if meta.get("tipo") == "oferta_licenciamento_terceiros":
            from services.ofertas_terceiros import on_payment_authorized
            try:
                on_payment_authorized(
                    session_id=obj.get("id") if isinstance(obj, dict) else obj.id,
                    payment_intent_id=obj.get("payment_intent") if isinstance(obj, dict) else obj.payment_intent,
                )
            except Exception as e:
                logger.exception("Falha em on_payment_authorized: %s", e)
            return jsonify({"received": True}), 200

        # Pode ser: licença one-time (mode=payment) OU assinatura PRO (mode=subscription)
        mode = obj.get("mode") if isinstance(obj, dict) else getattr(obj, "mode", None)
        if mode == "subscription":
            from services.subscription import on_checkout_completed
            try: on_checkout_completed(obj if isinstance(obj, dict) else obj.to_dict())
            except Exception as e: logger.error(f"Falha ao ativar PRO: {e}")
            return jsonify({"received": True}), 200

        session_id     = obj.get("id") if isinstance(obj, dict) else obj.id
        payment_intent = obj.get("payment_intent") if isinstance(obj, dict) else obj.payment_intent

        # Atualiza transação
        result = sb.table("transacoes").update({
            "status":                "confirmada",
            "stripe_payment_intent": payment_intent,
            "confirmed_at":          "now()",
        }).eq("stripe_session_id", session_id).execute()

        # CORREÇÃO #14 (MÉDIA): Audit log
        if result.data:
            trans = result.data[0]
            AuditLogger.log_compra(
                trans["id"],
                trans["obra_id"],
                trans["valor_cents"]
            )

            # Dispara geração do Contrato de Licenciamento (Cláusulas ECAD/split/etc)
            try:
                from services.contrato_licenciamento import gerar_contrato_licenciamento
                gerar_contrato_licenciamento(trans["id"])
            except Exception as _e:
                logger.warning(f"Falha ao gerar contrato de licenciamento: {_e}")

            # Credita wallets dos autores (saque manual via Stripe depois)
            try:
                from services.repasses import creditar_wallets_por_transacao
                resultado = creditar_wallets_por_transacao(trans["id"])
                logger.info("Wallets creditadas %s: %s", trans["id"], resultado)
            except Exception as _e:
                logger.error("Falha ao creditar wallets: %s", _e)

    elif event_type == "payment_intent.succeeded":
        # Backup: se checkout.session.completed não disparou, garante crédito
        pi_id = obj.get("id") if isinstance(obj, dict) else obj.id
        trans = sb.table("transacoes").select("id").eq(
            "stripe_payment_intent", pi_id
        ).limit(1).execute().data
        if trans:
            try:
                from services.repasses import creditar_wallets_por_transacao
                creditar_wallets_por_transacao(trans[0]["id"])
            except Exception as _e:
                logger.warning("Backup credito wallet (PI succeeded) falhou: %s", _e)

    elif event_type in ("checkout.session.expired", "payment_intent.payment_failed"):
        session_id = obj.get("id") if isinstance(obj, dict) else obj.id
        sb.table("transacoes").update({
            "status": "cancelada",
        }).eq("stripe_session_id", session_id).execute()

    # ── Stripe Connect: status da conta do compositor ───────────
    elif event_type == "account.updated":
        acc_id = obj.get("id") if isinstance(obj, dict) else obj.id
        charges_ok = bool(obj.get("charges_enabled"))
        payouts_ok = bool(obj.get("payouts_enabled"))
        details_ok = bool(obj.get("details_submitted"))

        # Atualiza perfil + libera repasses retidos (se virou apto agora)
        upd = sb.table("perfis").update({
            "stripe_charges_enabled":      charges_ok,
            "stripe_payouts_enabled":      payouts_ok,
            "stripe_onboarding_completo":  details_ok and charges_ok,
            "stripe_account_atualizado_em": "now()",
        }).eq("stripe_account_id", acc_id).execute()

        # Wallet+saque manual: nada a liberar automaticamente quando a conta fica apta.
        # O usuário simplesmente passa a conseguir clicar "Solicitar saque".
        if charges_ok:
            logger.info("Conta Connect %s ficou apta a receber transfers.", acc_id)

    elif event_type == "account.application.deauthorized":
        acc_id = obj.get("id") if isinstance(obj, dict) else obj.id
        sb.table("perfis").update({
            "stripe_account_id":           None,
            "stripe_charges_enabled":      False,
            "stripe_payouts_enabled":      False,
            "stripe_onboarding_completo":  False,
        }).eq("stripe_account_id", acc_id).execute()
        logger.warning("Conta Connect %s desautorizou a plataforma", acc_id)

    # ── Transfers (repasses) ────────────────────────────────────
    elif event_type == "transfer.failed":
        transfer_id = obj.get("id") if isinstance(obj, dict) else obj.id
        sb.table("repasses").update({
            "status":   "falhou",
            "erro_msg": "Transfer falhou (webhook transfer.failed)",
        }).eq("stripe_transfer_id", transfer_id).execute()
        logger.error("Transfer falhou: %s", transfer_id)

    elif event_type == "payout.failed":
        # Payout (banco) falhou — apenas log; o autor recebe email da Stripe
        logger.error("Payout falhou: %s", obj.get("id") if isinstance(obj, dict) else obj.id)

    # ── Reembolsos: reverter transfers ──────────────────────────
    elif event_type == "charge.refunded":
        pi_id = obj.get("payment_intent") if isinstance(obj, dict) else obj.payment_intent
        if pi_id:
            trans = sb.table("transacoes").select("id").eq(
                "stripe_payment_intent", pi_id
            ).limit(1).execute().data
            if trans:
                from services.repasses import reverter_repasses_de_transacao
                try:
                    reverter_repasses_de_transacao(trans[0]["id"], motivo="charge.refunded")
                    sb.table("transacoes").update({"status": "reembolsada"}).eq("id", trans[0]["id"]).execute()
                except Exception as _e:
                    logger.error("Falha ao reverter repasses: %s", _e)

    # ── Assinaturas PRO ─────────────────────────────────────────
    elif event_type == "customer.subscription.updated":
        from services.subscription import on_subscription_updated
        try: on_subscription_updated(obj if isinstance(obj, dict) else obj.to_dict())
        except Exception as e: logger.error(f"subscription.updated: {e}")

    elif event_type == "customer.subscription.deleted":
        from services.subscription import on_subscription_deleted
        try: on_subscription_deleted(obj if isinstance(obj, dict) else obj.to_dict())
        except Exception as e: logger.error(f"subscription.deleted: {e}")

    elif event_type == "invoice.payment_failed":
        from services.subscription import on_invoice_payment_failed
        try: on_invoice_payment_failed(obj if isinstance(obj, dict) else obj.to_dict())
        except Exception as e: logger.error(f"invoice.payment_failed: {e}")

    return jsonify({"received": True}), 200


@stripe_bp.route("/sucesso/<session_id>", methods=["GET"])
@require_auth
def verificar_sucesso(session_id):
    if not stripe.api_key:
        abort(500, description="Stripe não configurado.")

    try:
        session = stripe.checkout.Session.retrieve(session_id)
    except stripe.error.StripeError as e:
        abort(404, description=f"Sessão não encontrada: {str(e)}")

    sb = get_supabase()
    trans = (
        sb.table("transacoes")
        .select("id, status, valor_cents, obras(nome)")
        .eq("stripe_session_id", session_id)
        .single()
        .execute()
    )
    if not trans.data:
        abort(404, description="Transação não encontrada.")

    # Confirma se Stripe pagou mas o webhook não rodou
    if session.payment_status == "paid" and trans.data["status"] == "pendente":
        sb.table("transacoes").update({
            "status":                "confirmada",
            "stripe_payment_intent": session.payment_intent,
            "confirmed_at":          "now()",
        }).eq("stripe_session_id", session_id).execute()
        trans.data["status"] = "confirmada"

    return jsonify({
        "transacao":     trans.data,
        "stripe_status": session.payment_status,
        "obra_nome":     trans.data.get("obras", {}).get("nome") if trans.data.get("obras") else None,
    }), 200
