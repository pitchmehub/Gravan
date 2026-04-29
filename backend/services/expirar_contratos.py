"""
Serviço: expiração de contratos de licenciamento não assinados.

Regra: se houver signatários humanos (autores/coautores) que não assinaram
dentro de SIGNING_DEADLINE_HORAS após a criação do contrato, o contrato é
cancelado e o comprador recebe reembolso integral via Stripe.

Chamado periodicamente pelo watchdog.
"""
import logging
import os
from datetime import datetime, timezone, timedelta

import stripe

from db.supabase_client import get_supabase

logger = logging.getLogger("gravan.expirar_contratos")

SIGNING_DEADLINE_HORAS = int(os.getenv("CONTRACT_SIGNING_DEADLINE_HORAS", "72"))

# Papéis que precisam de assinatura humana (excluindo Gravan e intérprete que
# assina automaticamente no checkout)
PAPEIS_HUMANOS = {"autor", "coautor"}


def _ensure_stripe():
    if not stripe.api_key:
        stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")


def expirar_contratos_nao_assinados() -> dict:
    """
    Verifica contratos pendentes criados há mais de SIGNING_DEADLINE_HORAS e que
    ainda possuem signatários humanos sem assinatura. Para cada um:

    1. Cancela o contrato (status = "cancelado").
    2. Emite reembolso integral via Stripe (charge.refund).
    3. Marca a transação como "reembolsada".
    4. Notifica o comprador e o(s) autor(es).

    Retorna: dict com contadores de expirados, reembolsados e erros.
    """
    _ensure_stripe()
    sb = get_supabase()

    deadline = datetime.now(timezone.utc) - timedelta(hours=SIGNING_DEADLINE_HORAS)
    deadline_iso = deadline.isoformat()

    # Contratos pendentes criados antes do deadline
    try:
        rows = (
            sb.table("contracts")
            .select("id, transacao_id, buyer_id, seller_id, valor_cents, obra_id, obras(nome)")
            .eq("status", "pendente")
            .lt("created_at", deadline_iso)
            .execute()
            .data or []
        )
    except Exception as e:
        logger.error("Falha ao buscar contratos pendentes: %s", e)
        return {"status": "erro", "erro": str(e)}

    expirados = 0
    reembolsados = 0
    erros = 0

    for c in rows:
        contract_id = c["id"]
        try:
            # Verifica se há signatários humanos que ainda não assinaram
            signers = (
                sb.table("contract_signers")
                .select("user_id, role, signed")
                .eq("contract_id", contract_id)
                .execute()
                .data or []
            )
            pendentes_humanos = [
                s for s in signers
                if s.get("role") in PAPEIS_HUMANOS and not s.get("signed")
            ]
            if not pendentes_humanos:
                # Todos assinaram ou não há signatários humanos — não expira
                continue

            obra_nome = (c.get("obras") or {}).get("nome") or "obra"

            # 1. Cancela o contrato
            sb.table("contracts").update({
                "status": "cancelado",
            }).eq("id", contract_id).execute()

            try:
                sb.table("contract_events").insert({
                    "contract_id": contract_id,
                    "event_type":  "expirado",
                    "payload":     {
                        "motivo":    "prazo_assinatura_72h",
                        "deadline":  deadline_iso,
                        "pendentes": [s["user_id"] for s in pendentes_humanos],
                    },
                }).execute()
            except Exception:
                pass

            expirados += 1
            logger.info("Contrato %s cancelado por falta de assinatura em 72h.", contract_id)

            # 2. Reembolso Stripe
            transacao_id = c.get("transacao_id")
            if transacao_id:
                try:
                    trans = (
                        sb.table("transacoes")
                        .select("id, stripe_payment_intent, status")
                        .eq("id", transacao_id)
                        .single()
                        .execute()
                        .data or {}
                    )
                    pi_id = trans.get("stripe_payment_intent")
                    if pi_id and trans.get("status") == "confirmada":
                        pi = stripe.PaymentIntent.retrieve(pi_id)
                        charge_id = None
                        if pi.get("latest_charge"):
                            charge_id = (
                                pi["latest_charge"]
                                if isinstance(pi["latest_charge"], str)
                                else pi["latest_charge"]["id"]
                            )
                        if charge_id:
                            stripe.Refund.create(
                                charge=charge_id,
                                metadata={
                                    "motivo":      "contrato_nao_assinado_72h",
                                    "contract_id": contract_id,
                                    "transacao_id": transacao_id,
                                },
                            )
                            sb.table("transacoes").update({
                                "status": "reembolsada",
                            }).eq("id", transacao_id).execute()
                            reembolsados += 1
                            logger.info(
                                "Reembolso emitido para transação %s (charge %s).",
                                transacao_id, charge_id,
                            )
                        else:
                            logger.warning(
                                "Contrato %s: nenhum charge encontrado no PI %s.",
                                contract_id, pi_id,
                            )
                except Exception as e_ref:
                    logger.error(
                        "Falha ao reembolsar transação %s: %s", transacao_id, e_ref
                    )
                    erros += 1

            # 3. Notificações
            try:
                from services.notificacoes import notify as _notify
                valor_reais = (
                    f"R$ {c['valor_cents'] / 100:,.2f}"
                    .replace(",", "X").replace(".", ",").replace("X", ".")
                ) if c.get("valor_cents") else ""

                # Comprador
                if c.get("buyer_id"):
                    _notify(
                        c["buyer_id"],
                        tipo="reembolso",
                        titulo="Licenciamento cancelado — reembolso em processamento",
                        mensagem=(
                            f"O licenciamento da obra \"{obra_nome}\" foi cancelado porque "
                            f"o(s) autor(es) não assinaram o contrato dentro do prazo de "
                            f"{SIGNING_DEADLINE_HORAS}h. "
                            + (f"O valor de {valor_reais} será devolvido ao método de pagamento original." if valor_reais else "")
                        ),
                        link="/contratos",
                        payload={"contract_id": contract_id},
                    )

                # Autor(es) que não assinaram
                nao_assinaram_ids = [s["user_id"] for s in pendentes_humanos]
                for uid in nao_assinaram_ids:
                    _notify(
                        uid,
                        tipo="contrato_expirado",
                        titulo="Contrato de licenciamento expirado",
                        mensagem=(
                            f"O contrato de licenciamento da obra \"{obra_nome}\" foi "
                            f"cancelado automaticamente porque não foi assinado dentro do "
                            f"prazo de {SIGNING_DEADLINE_HORAS} horas. "
                            f"O comprador receberá reembolso integral."
                        ),
                        link="/contratos",
                        payload={"contract_id": contract_id},
                    )
            except Exception as e_not:
                logger.warning("Falha ao notificar partes do contrato %s: %s", contract_id, e_not)

        except Exception as e:
            erros += 1
            logger.error("Erro ao processar contrato %s: %s", contract_id, e)

    logger.info(
        "Expiração concluída: %d expirados, %d reembolsados, %d erros.",
        expirados, reembolsados, erros,
    )
    return {
        "status":      "ok",
        "expirados":   expirados,
        "reembolsados": reembolsados,
        "erros":       erros,
    }
