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
from datetime import datetime, timezone
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
    oferta_id = data.get("oferta_id")  # opcional: paga uma oferta aceita
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

    sb = get_supabase()

    # Se foi passado oferta_id, valida e usa o valor da oferta no lugar de preco_cents
    oferta = None
    if oferta_id:
        oferta = sb.table("ofertas").select(
            "id, obra_id, interprete_id, valor_cents, status, tipo, aguardando_resposta_de"
        ).eq("id", oferta_id).single().execute().data
        if not oferta:
            abort(404, description="Oferta não encontrada.")
        if oferta["interprete_id"] != g.user.id:
            abort(403, description="Esta oferta não pertence a você.")
        if oferta["status"] != "aceita":
            abort(409, description=f"Oferta em status '{oferta['status']}' — só ofertas aceitas podem ser pagas.")
        # Vincula obra_id da oferta (sobrescreve qualquer obra_id do body)
        obra_id = oferta["obra_id"]

    # Proteção anti-auto-compra: titular não pode comprar sua propria obra
    obra_check = sb_check.table("obras").select("titular_id, is_exclusive, exclusive_to_id").eq("id", obra_id).single().execute()
    if obra_check.data and obra_check.data.get("titular_id") == g.user.id:
        abort(422, description="Voce nao pode comprar uma obra de sua propria autoria.")
    # Bloqueia compras em obra sob exclusividade (exceto se for o próprio exclusivista)
    if obra_check.data and obra_check.data.get("is_exclusive"):
        if obra_check.data.get("exclusive_to_id") != g.user.id:
            abort(409, description="Esta obra está sob contrato de exclusividade ativa.")

    if not obra_id:
        abort(422, description="obra_id obrigatório.")
    if metodo not in METODO_TO_STRIPE:
        abort(422, description=f"Método inválido: {metodo}")

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

    # Se houver oferta, usa o valor pactuado (sobrescreve preco_cents)
    valor_unit = oferta["valor_cents"] if oferta else obra["preco_cents"]

    # Nome, plano e editora do compositor titular (fee depende do plano;
    # 10% adicional vai para a editora vinculada, se existir)
    try:
        titular = sb.table("perfis").select(
            "nome, plano, status_assinatura, publisher_id"
        ).eq("id", obra["titular_id"]).single().execute()
        t_data = titular.data or {}
    except Exception:
        titular = sb.table("perfis").select("nome").eq("id", obra["titular_id"]).single().execute()
        t_data = {**(titular.data or {}), "plano": "STARTER", "status_assinatura": "inativa", "publisher_id": None}
    titular_nome  = t_data.get("nome", "Gravan")
    plano_titular = t_data.get("plano", "STARTER")
    status_ass    = t_data.get("status_assinatura", "inativa")
    publisher_id  = t_data.get("publisher_id")
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
        split = calcular_split(
            valor_unit,
            coautorias,
            plano_titular=plano_titular,
            publisher_id=publisher_id,
        )
    except ValueError as e:
        abort(422, description=str(e))

    # Descrição do produto: distingue licença normal de exclusividade
    eh_exclusividade = bool(oferta and oferta.get("tipo") == "exclusividade")
    nome_produto = (f"Licença EXCLUSIVA (5 anos): {obra['nome']}"
                    if eh_exclusividade else f"Licença: {obra['nome']}")
    desc_produto = (f"Exclusividade adquirida via oferta — composição de {titular_nome}"
                    if eh_exclusividade else f"Composição musical de {titular_nome}")

    # Cria a sessão Stripe
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=METODO_TO_STRIPE[metodo],
            mode="payment",
            line_items=[{
                "price_data": {
                    "currency": "brl",
                    "product_data": {
                        "name": nome_produto,
                        "description": desc_produto,
                    },
                    "unit_amount": valor_unit,
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
                "oferta_id":    (oferta or {}).get("id", ""),
                "oferta_tipo":  (oferta or {}).get("tipo", ""),
            },
        )
    except stripe.StripeError as e:
        msg = e.user_message or str(e)
        abort(500, description=f"Erro Stripe: {msg}")
    except Exception as e:
        abort(500, description=f"Erro ao criar checkout: {str(e)}")

    # Salva transação como pendente
    from utils.crypto import hash_ip
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
                "oferta_id":       (oferta or {}).get("id"),
                "oferta_tipo":     (oferta or {}).get("tipo"),
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
            
    except stripe.SignatureVerificationError as e:
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
            "confirmed_at":          datetime.utcnow().isoformat() + "Z",
        }).eq("stripe_session_id", session_id).execute()

        # CORREÇÃO #14 (MÉDIA): Audit log
        if result.data:
            trans = result.data[0]
            AuditLogger.log_compra(
                trans["id"],
                trans["obra_id"],
                trans["valor_cents"]
            )

            # Se a compra veio de uma oferta, marca-a como paga.
            # Se for oferta de exclusividade, aplica exclusividade na obra.
            try:
                meta_oferta_id = (meta or {}).get("oferta_id") or ""
                meta_oferta_tipo = (meta or {}).get("oferta_tipo") or ""
                if meta_oferta_id:
                    sb.table("ofertas").update({
                        "status": "paga",
                    }).eq("id", meta_oferta_id).execute()
                if meta_oferta_tipo == "exclusividade":
                    from services.ofertas import aplicar_exclusividade_em_obra
                    aplicar_exclusividade_em_obra(
                        obra_id=trans["obra_id"],
                        comprador_id=trans["comprador_id"],
                    )
            except Exception as _e:
                logger.warning("Falha ao processar pós-pagamento de oferta: %s", _e)

            # Dispara geração do Contrato de Licenciamento (Cláusulas ECAD/split/etc)
            # IMPORTANTE: as wallets só são creditadas após todas as partes assinarem
            # o contrato (escrow). O crédito ocorre em aceitar_contrato() quando
            # todos_assinaram=True.
            try:
                from services.contrato_licenciamento import gerar_contrato_licenciamento
                gerar_contrato_licenciamento(trans["id"])
            except Exception as _e:
                logger.warning(f"Falha ao gerar contrato de licenciamento: {_e}")

            # Push/notificação para o compositor e o comprador
            obra_info = {}
            try:
                from services.notificacoes import notify as _notify
                obra_info = sb.table("obras").select("nome, titular_id").eq(
                    "id", trans["obra_id"]
                ).single().execute().data or {}
                comprador_info = sb.table("perfis").select("nome").eq(
                    "id", trans["comprador_id"]
                ).single().execute().data or {}
                titular_id = obra_info.get("titular_id")
                if titular_id and titular_id != trans.get("comprador_id"):
                    valor_reais = f"R$ {trans['valor_cents'] / 100:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                    _notify(
                        perfil_id=titular_id,
                        tipo="compra",
                        titulo=f"Sua obra foi licenciada: \"{obra_info.get('nome','—')}\"",
                        mensagem=(
                            f"{comprador_info.get('nome') or 'Um intérprete'} licenciou "
                            f"\"{obra_info.get('nome','—')}\" por {valor_reais}. "
                            f"O valor será liberado na sua carteira após todas as partes assinarem o contrato."
                        ),
                        link="/contratos",
                        payload={
                            "transacao_id": trans["id"],
                            "obra_id":      trans["obra_id"],
                            "valor_cents":  trans["valor_cents"],
                        },
                    )
            except Exception as _e:
                logger.warning("Falha ao notificar compositor da compra: %s", _e)

            # Push/notificação para o comprador: compra confirmada
            try:
                from services.notificacoes import notify as _notify2
                if not obra_info:
                    obra_info = sb.table("obras").select("nome, titular_id").eq(
                        "id", trans["obra_id"]
                    ).single().execute().data or {}
                valor_reais_comprador = f"R$ {trans['valor_cents'] / 100:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                _notify2(
                    perfil_id=trans["comprador_id"],
                    tipo="compra",
                    titulo=f"Compra confirmada: \"{obra_info.get('nome','—')}\"",
                    mensagem=(
                        f"Seu pagamento de {valor_reais_comprador} foi aprovado. "
                        f"Acesse seus contratos para baixar a licença."
                    ),
                    link="/contratos",
                    payload={
                        "transacao_id": trans["id"],
                        "obra_id":      trans["obra_id"],
                        "valor_cents":  trans["valor_cents"],
                    },
                )
            except Exception as _e:
                logger.warning("Falha ao notificar comprador da compra: %s", _e)

    elif event_type == "payment_intent.succeeded":
        # Backup: garante que o contrato foi gerado caso checkout.session.completed
        # não tenha disparado. As wallets SÃO creditadas apenas após todas as partes
        # assinarem o contrato (em aceitar_contrato). Não creditamos aqui.
        pi_id = obj.get("id") if isinstance(obj, dict) else obj.id
        trans = sb.table("transacoes").select("id").eq(
            "stripe_payment_intent", pi_id
        ).limit(1).execute().data
        if trans:
            try:
                from services.contrato_licenciamento import gerar_contrato_licenciamento
                gerar_contrato_licenciamento(trans[0]["id"])
            except Exception as _e:
                logger.warning("Backup gerar contrato (PI succeeded) falhou: %s", _e)

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
            "stripe_account_atualizado_em": datetime.utcnow().isoformat() + "Z",
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
        logger.error("verificar_sucesso: STRIPE_SECRET_KEY ausente")
        return jsonify({"error": "Stripe não configurado no servidor."}), 500

    # 1) Recupera a sessão no Stripe
    try:
        session = stripe.checkout.Session.retrieve(session_id)
    except stripe.StripeError as e:
        logger.warning("verificar_sucesso: sessão Stripe inválida (%s): %s", session_id, e)
        return jsonify({"error": "Sessão de pagamento não encontrada no Stripe."}), 404
    except Exception as e:
        logger.exception("verificar_sucesso: erro inesperado ao recuperar sessão %s", session_id)
        return jsonify({"error": f"Falha ao consultar Stripe: {str(e)}"}), 500

    sb = get_supabase()

    # 2) Busca a transação (sem join — evita falha caso a FK não esteja exposta no PostgREST)
    try:
        resp = (
            sb.table("transacoes")
            .select("id, status, valor_cents, obra_id")
            .eq("stripe_session_id", session_id)
            .limit(1)
            .execute()
        )
        rows = resp.data or []
    except Exception as e:
        logger.exception("verificar_sucesso: erro ao buscar transação %s", session_id)
        return jsonify({"error": f"Falha ao consultar transação: {str(e)}"}), 500

    if not rows:
        # Fallback: a transação ainda não foi criada no banco (raro). Devolve só status do Stripe.
        logger.info("verificar_sucesso: transação ausente para session_id=%s; devolvendo só status Stripe", session_id)
        return jsonify({
            "transacao":     None,
            "stripe_status": session.payment_status,
            "obra_nome":     None,
        }), 200

    trans = rows[0]

    # 3) Confirma se Stripe pagou mas o webhook ainda não rodou
    try:
        if session.payment_status == "paid" and trans.get("status") == "pendente":
            sb.table("transacoes").update({
                "status":                "confirmada",
                "stripe_payment_intent": session.payment_intent,
                "confirmed_at":          datetime.utcnow().isoformat() + "Z",
            }).eq("stripe_session_id", session_id).execute()
            trans["status"] = "confirmada"
    except Exception as e:
        logger.exception("verificar_sucesso: falha ao atualizar transação para confirmada (%s)", session_id)

    # 4) Busca o nome da obra separadamente (não bloqueia a resposta se falhar)
    obra_nome = None
    try:
        if trans.get("obra_id"):
            o = (
                sb.table("obras")
                .select("nome")
                .eq("id", trans["obra_id"])
                .limit(1)
                .execute()
            )
            if o.data:
                obra_nome = o.data[0].get("nome")
    except Exception as e:
        logger.warning("verificar_sucesso: falha ao buscar nome da obra %s: %s", trans.get("obra_id"), e)

    return jsonify({
        "transacao":     trans,
        "stripe_status": session.payment_status,
        "obra_nome":     obra_nome,
    }), 200
