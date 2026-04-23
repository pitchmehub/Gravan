"""
Routes: /api/paypal — PayPal integration

CORREÇÕES DE SEGURANÇA / PENTEST:
- execute_payment: assinatura de calcular_split corrigida (estava quebrada)
- request.json acessado de forma segura (não crasha se body vazio)
- Validação de cadastro_completo + concordo_contrato (antes só Stripe validava)
- Anti-auto-compra e anti-duplicidade mantidos
"""
from flask import Blueprint, request, jsonify, g, abort
from middleware.auth import require_auth
from db.supabase_client import get_supabase
from services.paypal_service import PayPalService
from services.finance import calcular_split
from utils.audit import AuditLogger
from utils.crypto import hash_ip
from app import limiter
from datetime import datetime, timezone
import os
import logging

logger = logging.getLogger("pitchme.paypal")

paypal_bp = Blueprint("paypal", __name__)

FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")


def _safe_json():
    """request.json pode ser None se Content-Type não for JSON."""
    try:
        return request.get_json(silent=True) or {}
    except Exception:
        return {}


@paypal_bp.route("/create-payment", methods=["POST"])
@require_auth
@limiter.limit("5 per minute")
def create_payment():
    """
    Cria um pagamento PayPal para compra de obra.
    """
    data = _safe_json()
    obra_id = data.get("obra_id")
    concordou_contrato = bool(data.get("concordo_contrato", False))

    if not obra_id:
        abort(422, description="obra_id é obrigatório.")

    sb = get_supabase()

    # Comprador precisa ter cadastro completo (mesma regra do Stripe)
    perfil_check = sb.table("perfis").select("cadastro_completo").eq("id", g.user.id).single().execute()
    if not perfil_check.data:
        abort(404, description="Perfil não encontrado.")
    if not perfil_check.data.get("cadastro_completo"):
        abort(422, description="Complete seu cadastro (CPF, RG, endereço) antes de comprar.")

    if not concordou_contrato:
        abort(422, description="Marque a caixa de concordância com o contrato antes de prosseguir.")

    obra_resp = sb.table("obras").select("id, preco_cents, status, titular_id").eq("id", obra_id).single().execute()
    if not obra_resp.data:
        abort(404, description="Obra não encontrada.")

    obra = obra_resp.data
    if obra.get("status") != "publicada":
        abort(422, description="Obra não disponível para compra.")
    if obra.get("titular_id") == g.user.id:
        abort(422, description="Você não pode comprar sua própria obra.")

    preco_cents = obra.get("preco_cents")
    if not preco_cents or preco_cents < 100:
        abort(422, description="Obra com preço inválido.")

    compra_existente = (
        sb.table("transacoes")
        .select("id")
        .eq("obra_id", obra_id)
        .eq("comprador_id", g.user.id)
        .eq("status", "confirmada")
        .execute()
    )
    if compra_existente.data:
        abort(409, description="Você já possui esta obra.")

    return_url = f"{FRONTEND_URL}/pagamento/paypal/sucesso"
    cancel_url = f"{FRONTEND_URL}/pagamento/paypal/cancelado"

    result = PayPalService.create_payment(
        amount_cents=preco_cents,
        obra_id=obra_id,
        comprador_id=g.user.id,
        return_url=return_url,
        cancel_url=cancel_url,
    )

    if not result.get("success"):
        logger.error("PayPal create_payment falhou: %s", result.get("error"))
        abort(500, description="Erro ao criar pagamento PayPal.")

    transacao = sb.table("transacoes").insert({
        "obra_id":           obra_id,
        "comprador_id":      g.user.id,
        "valor_cents":       preco_cents,
        "metodo":            "paypal",
        "status":            "pendente",
        "paypal_payment_id": result["payment_id"],
        "metadata": {
            "contrato_aceito":   True,
            "aceite_ip_hash":    hash_ip(request.remote_addr or ""),
            "aceite_at":         datetime.now(timezone.utc).isoformat(),
            "aceite_user_agent": (request.headers.get("User-Agent") or "")[:200],
        },
    }).execute()

    return jsonify({
        "approval_url":  result["approval_url"],
        "payment_id":    result["payment_id"],
        "transacao_id":  transacao.data[0]["id"],
    }), 200


@paypal_bp.route("/execute-payment", methods=["POST"])
@require_auth
@limiter.limit("10 per minute")
def execute_payment():
    """
    Executa (confirma) um pagamento PayPal após aprovação do usuário.

    Aceita paymentId/PayerID via JSON body OU query string.
    """
    data = _safe_json()
    payment_id = data.get("paymentId") or request.args.get("paymentId")
    payer_id   = data.get("PayerID")   or request.args.get("PayerID")

    if not payment_id or not payer_id:
        abort(422, description="paymentId e PayerID são obrigatórios.")

    sb = get_supabase()

    trans_resp = (
        sb.table("transacoes")
        .select("*")
        .eq("paypal_payment_id", payment_id)
        .eq("comprador_id", g.user.id)
        .single()
        .execute()
    )
    if not trans_resp.data:
        abort(404, description="Transação não encontrada.")

    transacao = trans_resp.data
    if transacao.get("status") == "confirmada":
        # Idempotente — segunda chamada apenas reporta sucesso, não duplica crédito
        return jsonify({"success": True, "transacao": transacao, "message": "Já confirmada."}), 200

    result = PayPalService.execute_payment(payment_id, payer_id)

    if not result.get("success"):
        sb.table("transacoes").update({"status": "cancelada"}).eq("id", transacao["id"]).execute()
        logger.error("PayPal execute falhou: %s", result.get("error"))
        abort(500, description="Erro ao executar pagamento.")

    # Calcula split (assinatura correta do finance.calcular_split)
    obra_resp = sb.table("obras").select("titular_id").eq("id", transacao["obra_id"]).single().execute()
    if not obra_resp.data:
        abort(500, description="Obra associada à transação não encontrada.")
    titular_id = obra_resp.data["titular_id"]

    coaut = sb.table("coautorias").select("perfil_id, share_pct").eq("obra_id", transacao["obra_id"]).execute()
    coautorias = coaut.data or [{"perfil_id": titular_id, "share_pct": 100}]

    # Plano do titular afeta o split
    try:
        titular = sb.table("perfis").select("plano, status_assinatura").eq("id", titular_id).single().execute()
        t = titular.data or {}
    except Exception:
        t = {}
    plano_titular = t.get("plano", "STARTER")
    if plano_titular == "PRO" and t.get("status_assinatura") not in ("ativa", "cancelada", "past_due"):
        plano_titular = "STARTER"

    try:
        split = calcular_split(transacao["valor_cents"], coautorias, plano_titular=plano_titular)
    except ValueError as e:
        logger.error("Split inválido: %s", e)
        abort(500, description="Erro ao calcular split.")

    sb.table("transacoes").update({
        "status":           "confirmada",
        "plataforma_cents": split.plataforma_cents,
        "liquido_cents":    split.liquido_cents,
        "payer_email":      result.get("payer_email"),
        "confirmed_at":     "now()",
    }).eq("id", transacao["id"]).execute()

    # Credita as wallets dos compositores (RPC creditar_wallet definida no schema do Supabase)
    for payout in split.payouts:
        try:
            sb.rpc("creditar_wallet", {
                "p_perfil_id":  payout["perfil_id"],
                "p_valor_cents": payout["valor_cents"],
                "p_origem":     f"venda_obra_{transacao['obra_id']}",
            }).execute()
        except Exception as e:
            # Se a RPC não existir, faz fallback direto na tabela wallets
            logger.warning("RPC creditar_wallet falhou (%s), fazendo fallback.", e)
            try:
                w = sb.table("wallets").select("saldo_cents").eq("perfil_id", payout["perfil_id"]).maybe_single().execute()
                saldo_atual = ((w.data if w else None) or {}).get("saldo_cents", 0) or 0
                novo = int(saldo_atual) + int(payout["valor_cents"])
                sb.table("wallets").upsert({"perfil_id": payout["perfil_id"], "saldo_cents": novo}).execute()
            except Exception as e2:
                logger.error("Fallback wallet falhou para %s: %s", payout["perfil_id"], e2)

    AuditLogger.log_compra(transacao["id"], transacao["obra_id"], transacao["valor_cents"])

    # Gera contrato de licenciamento (mesmo fluxo do Stripe)
    try:
        from services.contrato_licenciamento import gerar_contrato_licenciamento
        gerar_contrato_licenciamento(transacao["id"])
    except Exception as e:
        logger.warning("Falha ao gerar contrato de licenciamento PayPal: %s", e)

    return jsonify({
        "success":   True,
        "transacao": transacao,
        "message":   "Pagamento confirmado com sucesso!",
    }), 200


@paypal_bp.route("/payment/<payment_id>", methods=["GET"])
@require_auth
def get_payment_status(payment_id: str):
    """Consulta status de um pagamento PayPal (apenas o próprio comprador)."""
    sb = get_supabase()
    owner = (
        sb.table("transacoes")
        .select("id")
        .eq("paypal_payment_id", payment_id)
        .eq("comprador_id", g.user.id)
        .maybe_single()
        .execute()
    )
    if not owner or not owner.data:
        abort(404, description="Pagamento não encontrado.")

    result = PayPalService.get_payment_details(payment_id)
    if not result.get("success"):
        abort(404, description="Pagamento não encontrado.")
    return jsonify(result), 200
