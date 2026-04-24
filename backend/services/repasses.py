"""
Service: criação e liberação de repasses (Transfers Stripe Connect).

Regra B confirmada pelo usuário:
  - Se o autor NÃO tiver conta Connect ativa, o valor fica RETIDO.
  - Quando ele completa o onboarding (webhook account.updated), liberamos.

Taxas Stripe são deduzidas ANTES do split (item 9): usamos o `net` do
balance_transaction como base de cálculo, então todos pagam proporcionalmente.
"""
import os
import logging
from decimal import Decimal, ROUND_DOWN
from typing import Optional

import stripe

from db.supabase_client import get_supabase
from services.finance import fee_rate_for_plano

logger = logging.getLogger("gravan.repasses")


def _ensure_key():
    if not stripe.api_key:
        stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")


def _net_cents_do_charge(payment_intent_id: str) -> Optional[int]:
    """
    Retorna o valor LÍQUIDO (em centavos) que entrou no balance da plataforma
    para esse PaymentIntent. Já é descontado das taxas Stripe.
    """
    _ensure_key()
    try:
        pi = stripe.PaymentIntent.retrieve(
            payment_intent_id,
            expand=["latest_charge.balance_transaction"],
        )
        charge = pi.get("latest_charge")
        if not charge:
            return None
        bt = charge.get("balance_transaction")
        if not bt:
            return None
        # bt.net é o líquido após taxas Stripe, na moeda da conta (BRL)
        return int(bt["net"])
    except Exception as e:
        logger.error("Falha ao buscar net do PaymentIntent %s: %s", payment_intent_id, e)
        return None


def _calcular_split_sobre_net(net_cents: int, plano_titular: str, coautorias: list) -> dict:
    """
    Calcula:
      - plataforma_cents (taxa da Gravan sobre o NET)
      - distribuicao por coautor (com share_pct)
    """
    if net_cents <= 0:
        return {"plataforma_cents": 0, "payouts": []}

    rate = fee_rate_for_plano(plano_titular)
    net = Decimal(str(net_cents))
    plataforma = (net * rate).to_integral_value(ROUND_DOWN)
    liquido_autores = net - plataforma

    payouts = []
    distribuido = Decimal("0")
    for i, c in enumerate(coautorias):
        pct = Decimal(str(c["share_pct"]))
        if i == len(coautorias) - 1:
            v = int(liquido_autores - distribuido)
        else:
            v = int((liquido_autores * pct / Decimal("100")).to_integral_value(ROUND_DOWN))
            distribuido += Decimal(str(v))
        payouts.append({
            "perfil_id":   c["perfil_id"],
            "valor_cents": v,
            "share_pct":   float(pct),
        })

    return {
        "plataforma_cents": int(plataforma),
        "liquido_autores_cents": int(liquido_autores),
        "payouts": payouts,
    }


def creditar_wallets_por_transacao(transacao_id: str) -> dict:
    """
    Chamado pelo webhook após uma venda confirmada.
    Calcula o split (sobre o NET Stripe) e CREDITA na wallet de cada autor.
    NÃO dispara Transfer — o autor saca manualmente em /saques.
    Idempotente: se já creditou pra essa transação, não duplica.
    """
    sb = get_supabase()

    # Idempotência: se já tem registro de pagamento, ignora
    ja = sb.table("pagamentos_compositores").select("id").eq(
        "transacao_id", transacao_id
    ).limit(1).execute()
    if ja.data:
        logger.info("Wallets já creditadas para transação %s", transacao_id)
        return {"status": "ja_creditado"}

    trans = sb.table("transacoes").select(
        "id, obra_id, valor_cents, stripe_payment_intent, "
        "obras(id, titular_id)"
    ).eq("id", transacao_id).single().execute()
    if not trans.data:
        return {"status": "transacao_nao_encontrada"}
    t = trans.data
    obra = t.get("obras") or {}
    titular_id = obra.get("titular_id")
    pi_id = t.get("stripe_payment_intent")
    if not titular_id:
        return {"status": "obra_sem_titular"}

    # Net Stripe (taxas Stripe rateadas proporcionalmente — item 9)
    net = _net_cents_do_charge(pi_id) if pi_id else None
    if net is None:
        net = t["valor_cents"]

    titular = sb.table("perfis").select(
        "plano, status_assinatura"
    ).eq("id", titular_id).single().execute().data or {}
    plano = titular.get("plano", "STARTER")
    status_ass = titular.get("status_assinatura", "inativa")
    if plano == "PRO" and status_ass not in ("ativa", "cancelada", "past_due"):
        plano = "STARTER"

    coaut = sb.table("coautorias").select("perfil_id, share_pct").eq(
        "obra_id", t["obra_id"]
    ).execute()
    coautorias = coaut.data or [{"perfil_id": titular_id, "share_pct": 100}]

    split = _calcular_split_sobre_net(net, plano, coautorias)

    creditados = 0
    for p in split["payouts"]:
        if p["valor_cents"] <= 0:
            continue
        # Tenta RPC; fallback direto na tabela
        try:
            sb.rpc("creditar_wallet", {
                "p_perfil_id":   p["perfil_id"],
                "p_valor_cents": p["valor_cents"],
                "p_transacao_id": transacao_id,
            }).execute()
        except Exception as e:
            logger.warning("RPC creditar_wallet falhou: %s — fallback direto.", e)
            try:
                w = sb.table("wallets").select("saldo_cents").eq(
                    "perfil_id", p["perfil_id"]
                ).maybe_single().execute()
                saldo_atual = ((w.data if w else None) or {}).get("saldo_cents", 0) or 0
                novo = saldo_atual + p["valor_cents"]
                sb.table("wallets").upsert({
                    "perfil_id": p["perfil_id"], "saldo_cents": novo,
                }).execute()
            except Exception as e2:
                logger.error("Fallback wallet falhou para %s: %s", p["perfil_id"], e2)
                continue

        # Registra histórico de pagamento
        try:
            sb.table("pagamentos_compositores").insert({
                "perfil_id":    p["perfil_id"],
                "transacao_id": transacao_id,
                "valor_cents":  p["valor_cents"],
                "share_pct":    p["share_pct"],
            }).execute()
        except Exception as e:
            logger.warning("Falha ao gravar pagamentos_compositores: %s", e)
        creditados += 1

    return {
        "status": "ok",
        "net_cents": net,
        "plataforma_cents": split["plataforma_cents"],
        "creditados": creditados,
    }


def executar_saque_stripe(perfil_id: str, valor_cents: int) -> dict:
    """
    Solicita um saque via Stripe Connect.
    1. Valida que o perfil tem Connect ativo
    2. Valida saldo na wallet
    3. Cria Transfer Stripe → conta Connect do usuário
    4. Debita wallet + insere em `saques` com status='processando'
    Retorna dict com saque_id e stripe_transfer_id.
    """
    _ensure_key()
    sb = get_supabase()

    if valor_cents < 1000:
        raise ValueError("Valor mínimo: R$ 10,00")

    perfil = sb.table("perfis").select(
        "id, stripe_account_id, stripe_charges_enabled, stripe_payouts_enabled"
    ).eq("id", perfil_id).single().execute().data or {}
    acc_id = perfil.get("stripe_account_id")
    if not acc_id:
        raise ValueError("Você precisa conectar sua conta Stripe antes de sacar. "
                         "Vá em Receber Pagamentos.")
    if not perfil.get("stripe_charges_enabled"):
        raise ValueError("Sua conta Stripe ainda está em verificação. "
                         "Complete o cadastro em Receber Pagamentos.")

    # Saldo
    w = sb.table("wallets").select("saldo_cents").eq(
        "perfil_id", perfil_id
    ).maybe_single().execute()
    saldo = ((w.data if w else None) or {}).get("saldo_cents", 0) or 0
    if valor_cents > saldo:
        raise ValueError(f"Saldo insuficiente. Disponível: R$ {saldo/100:.2f}")

    # Cria registro de saque ANTES do transfer (pra ter ID pra idempotency_key)
    saque_ins = sb.table("saques").insert({
        "perfil_id":         perfil_id,
        "valor_cents":       valor_cents,
        "status":            "processando",
        "metodo":            "stripe",
        "stripe_account_id": acc_id,
    }).execute()
    if not saque_ins.data:
        raise RuntimeError("Não foi possível registrar o saque.")
    saque_id = saque_ins.data[0]["id"]

    # Cria o Transfer
    try:
        tr = stripe.Transfer.create(
            amount=valor_cents,
            currency="brl",
            destination=acc_id,
            metadata={"saque_id": str(saque_id), "perfil_id": str(perfil_id)},
            idempotency_key=f"saque_{saque_id}",
        )
    except stripe.error.StripeError as e:
        sb.table("saques").update({
            "status":   "rejeitado",
            "metadata": {"erro": (e.user_message or str(e))[:500]},
        }).eq("id", saque_id).execute()
        raise RuntimeError(f"Erro Stripe: {e.user_message or str(e)}")

    # Debita wallet + atualiza saque
    novo_saldo = saldo - valor_cents
    sb.table("wallets").upsert({
        "perfil_id": perfil_id, "saldo_cents": novo_saldo,
    }).execute()
    sb.table("saques").update({
        "status":             "pago",
        "stripe_transfer_id": tr.id,
    }).eq("id", saque_id).execute()

    return {
        "saque_id":           saque_id,
        "stripe_transfer_id": tr.id,
        "valor_cents":        valor_cents,
        "novo_saldo_cents":   novo_saldo,
    }


def gerar_repasses_para_transacao(transacao_id: str) -> dict:
    """
    [LEGADO/OPCIONAL] Modo de transfer automático por venda.
    Hoje a plataforma usa wallet+saque manual; mantido aqui caso queira reativar.
    """
    _ensure_key()
    sb = get_supabase()

    # Já gerado?
    existing = sb.table("repasses").select("id").eq("transacao_id", transacao_id).limit(1).execute()
    if existing.data:
        logger.info("Repasses já existem para transação %s — ignorando.", transacao_id)
        return {"status": "ja_existia", "qtd": len(existing.data)}

    trans = sb.table("transacoes").select(
        "id, obra_id, valor_cents, stripe_payment_intent, "
        "obras(id, titular_id)"
    ).eq("id", transacao_id).single().execute()
    if not trans.data:
        return {"status": "transacao_nao_encontrada"}
    t = trans.data
    obra = t.get("obras") or {}
    titular_id = obra.get("titular_id")
    pi_id = t.get("stripe_payment_intent")
    if not pi_id or not titular_id:
        logger.warning("Transação %s sem PI ou titular. Abortando split.", transacao_id)
        return {"status": "dados_insuficientes"}

    # Net real após taxas Stripe (item 9: repasse proporcional)
    net = _net_cents_do_charge(pi_id)
    if net is None:
        # Fallback conservador: usa valor bruto (sem deduzir taxas Stripe)
        net = t["valor_cents"]
        logger.warning("Usando valor BRUTO como base (net indisponível) para %s", transacao_id)

    # Plano efetivo do titular
    titular = sb.table("perfis").select(
        "plano, status_assinatura"
    ).eq("id", titular_id).single().execute().data or {}
    plano = titular.get("plano", "STARTER")
    status_ass = titular.get("status_assinatura", "inativa")
    if plano == "PRO" and status_ass not in ("ativa", "cancelada", "past_due"):
        plano = "STARTER"

    # Coautorias (com fallback 100% titular)
    coaut = sb.table("coautorias").select("perfil_id, share_pct").eq("obra_id", t["obra_id"]).execute()
    coautorias = coaut.data or [{"perfil_id": titular_id, "share_pct": 100}]

    split = _calcular_split_sobre_net(net, plano, coautorias)

    # Cria registros + dispara transfers
    enviados, retidos, falhas = 0, 0, 0
    for p in split["payouts"]:
        if p["valor_cents"] <= 0:
            continue
        # Status do destinatário
        dest = sb.table("perfis").select(
            "stripe_account_id, stripe_charges_enabled"
        ).eq("id", p["perfil_id"]).single().execute().data or {}
        dest_acc = dest.get("stripe_account_id")
        pode_transferir = dest_acc and dest.get("stripe_charges_enabled")

        repasse_row = {
            "transacao_id":      transacao_id,
            "perfil_id":         p["perfil_id"],
            "valor_cents":       p["valor_cents"],
            "share_pct":         p["share_pct"],
            "stripe_account_id": dest_acc,
            "status":            "retido" if not pode_transferir else "pendente",
            "metadata":          {
                "net_cents_base": net,
                "plano_titular":  plano,
            },
        }

        if not pode_transferir:
            sb.table("repasses").insert(repasse_row).execute()
            retidos += 1
            logger.info(
                "Repasse RETIDO: perfil %s sem Stripe Connect ativo (R$ %.2f)",
                p["perfil_id"], p["valor_cents"] / 100,
            )
            continue

        # Tenta criar o Transfer agora
        try:
            tr = stripe.Transfer.create(
                amount=p["valor_cents"],
                currency="brl",
                destination=dest_acc,
                transfer_group=f"OBRA_{t['obra_id']}_TRANS_{transacao_id}",
                metadata={
                    "transacao_id": transacao_id,
                    "perfil_id":    p["perfil_id"],
                    "obra_id":      t["obra_id"],
                },
                idempotency_key=f"transfer_{transacao_id}_{p['perfil_id']}",
            )
            repasse_row["stripe_transfer_id"] = tr.id
            repasse_row["status"] = "enviado"
            repasse_row["enviado_at"] = "now()"
            sb.table("repasses").insert(repasse_row).execute()
            enviados += 1
        except stripe.error.StripeError as e:
            repasse_row["status"]   = "falhou"
            repasse_row["erro_msg"] = (e.user_message or str(e))[:500]
            sb.table("repasses").insert(repasse_row).execute()
            falhas += 1
            logger.error("Falha no Transfer para %s: %s", p["perfil_id"], e)

    return {
        "status":      "ok",
        "net_cents":   net,
        "plataforma_cents": split["plataforma_cents"],
        "enviados":    enviados,
        "retidos":     retidos,
        "falhas":      falhas,
    }


def liberar_repasses_retidos(perfil_id: str) -> dict:
    """
    Quando o autor completa o onboarding (webhook account.updated com
    charges_enabled=true), libera todos os repasses dele que estavam retidos.
    """
    _ensure_key()
    sb = get_supabase()

    perfil = sb.table("perfis").select(
        "stripe_account_id, stripe_charges_enabled"
    ).eq("id", perfil_id).single().execute().data or {}
    if not perfil.get("stripe_account_id") or not perfil.get("stripe_charges_enabled"):
        return {"status": "ainda_nao_apto"}

    retidos = sb.table("repasses").select(
        "id, transacao_id, valor_cents, transacoes(obra_id)"
    ).eq("perfil_id", perfil_id).eq("status", "retido").execute().data or []

    if not retidos:
        return {"status": "nada_a_liberar"}

    enviados, falhas = 0, 0
    for rep in retidos:
        try:
            obra_id = (rep.get("transacoes") or {}).get("obra_id", "")
            tr = stripe.Transfer.create(
                amount=rep["valor_cents"],
                currency="brl",
                destination=perfil["stripe_account_id"],
                transfer_group=f"OBRA_{obra_id}_TRANS_{rep['transacao_id']}",
                metadata={
                    "transacao_id": rep["transacao_id"],
                    "perfil_id":    perfil_id,
                    "liberacao_pos_onboarding": "true",
                },
                idempotency_key=f"transfer_release_{rep['id']}",
            )
            sb.table("repasses").update({
                "stripe_transfer_id": tr.id,
                "stripe_account_id":  perfil["stripe_account_id"],
                "status":             "enviado",
                "enviado_at":         "now()",
                "liberado_at":        "now()",
            }).eq("id", rep["id"]).execute()
            enviados += 1
        except stripe.error.StripeError as e:
            sb.table("repasses").update({
                "status":   "falhou",
                "erro_msg": (e.user_message or str(e))[:500],
            }).eq("id", rep["id"]).execute()
            falhas += 1
            logger.error("Falha ao liberar repasse %s: %s", rep["id"], e)

    return {"status": "ok", "enviados": enviados, "falhas": falhas}


def reverter_repasses_de_transacao(transacao_id: str, motivo: str = "refund") -> dict:
    """Chamado em charge.refunded — cria reversals dos transfers já enviados."""
    _ensure_key()
    sb = get_supabase()
    enviados = sb.table("repasses").select("id, stripe_transfer_id").eq(
        "transacao_id", transacao_id
    ).eq("status", "enviado").execute().data or []

    revertidos = 0
    for r in enviados:
        if not r.get("stripe_transfer_id"):
            continue
        try:
            stripe.Transfer.create_reversal(
                r["stripe_transfer_id"],
                metadata={"motivo": motivo, "transacao_id": transacao_id},
            )
            sb.table("repasses").update({"status": "revertido"}).eq("id", r["id"]).execute()
            revertidos += 1
        except stripe.error.StripeError as e:
            logger.error("Falha ao reverter transfer %s: %s", r["stripe_transfer_id"], e)

    return {"status": "ok", "revertidos": revertidos}
