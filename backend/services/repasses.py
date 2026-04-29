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
from datetime import datetime
from decimal import Decimal, ROUND_DOWN
from typing import Optional

import stripe

from db.supabase_client import get_supabase
from services.finance import fee_rate_for_plano, EDITORA_RATE

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


def _calcular_split_sobre_net(
    net_cents: int,
    plano_titular: str,
    coautorias: list,
    publisher_id: str | None = None,
) -> dict:
    """
    Calcula:
      - plataforma_cents (taxa da Gravan sobre o NET)
      - editora_payout (10% para editora vinculada, se aplicável)
      - distribuição por coautor (com share_pct), sobre o que sobrar
    """
    if net_cents <= 0:
        return {"plataforma_cents": 0, "editora_payout": None, "payouts": []}

    rate = fee_rate_for_plano(plano_titular)
    net = Decimal(str(net_cents))
    plataforma = (net * rate).to_integral_value(ROUND_DOWN)

    # Editora (10%) — calculada sobre o NET bruto.
    editora_cents = Decimal("0")
    editora_payout = None
    if publisher_id:
        editora_cents = (net * EDITORA_RATE).to_integral_value(ROUND_DOWN)
        editora_payout = {
            "perfil_id":   publisher_id,
            "valor_cents": int(editora_cents),
            "share_pct":   float(EDITORA_RATE * Decimal("100")),
        }

    liquido_autores = net - plataforma - editora_cents

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
        "plataforma_cents":      int(plataforma),
        "editora_cents":         int(editora_cents),
        "editora_payout":        editora_payout,
        "liquido_autores_cents": int(liquido_autores),
        "payouts":               payouts,
    }


def creditar_wallets_por_transacao(
    transacao_id: str,
    publisher_id_override: str | None = None,
) -> dict:
    """
    Credita as wallets dos autores/coautores após o contrato de licenciamento
    ser concluído (todos assinaram). NÃO dispara Transfer — o autor saca
    manualmente em /saques.
    Idempotente: se já creditou pra essa transação, não duplica.

    ESCROW: Só credita se houver um contrato de licenciamento com
    status='concluído' vinculado a esta transação. Se o contrato ainda
    estiver 'pendente' (não assinado), bloqueia e loga o erro.

    `publisher_id_override`: se informado, usa essa editora (em vez do
    publisher_id do titular). Usado pelo fluxo de oferta trilateral
    para creditar a editora terceira que aceitou a oferta.
    """
    sb = get_supabase()

    # ── GUARDA DE ESCROW ────────────────────────────────────────────────────
    # Garante que o contrato de licenciamento está CONCLUÍDO (todas as partes
    # assinaram) antes de qualquer crédito de wallet.
    # Bloqueia QUALQUER caminho de código — webhook antigo, trigger, chamada
    # direta — que tente creditar antes da conclusão do contrato.
    #
    # Regras:
    #   • Contrato encontrado com status != 'concluído' → BLOQUEIA
    #   • Contrato NÃO encontrado                       → BLOQUEIA
    #     (o contrato é vinculado por transacao_id em todos os fluxos legítimos
    #      antes de creditar; ausência de contrato indica chamada prematura)
    #   • Contrato encontrado com status = 'concluído'  → PERMITE
    #   • Exceção ao consultar                          → BLOQUEIA (fail-safe)
    try:
        contract_row = sb.table("contracts").select("id, status").eq(
            "transacao_id", transacao_id
        ).limit(1).execute()

        if not contract_row.data:
            logger.error(
                "ESCROW BLOQUEADO: creditar_wallets_por_transacao para transação %s "
                "não encontrou contrato vinculado. Chamada prematura ou inválida. "
                "Wallets NÃO serão creditadas.",
                transacao_id,
            )
            return {"status": "escrow_bloqueado_sem_contrato"}

        contract_status = contract_row.data[0].get("status", "")
        if contract_status not in ("concluído", "concluido"):
            logger.error(
                "ESCROW BLOQUEADO: creditar_wallets_por_transacao para transação %s "
                "mas contrato está '%s' (esperado: 'concluído'). "
                "Wallets NÃO serão creditadas.",
                transacao_id,
                contract_status,
            )
            return {"status": "escrow_bloqueado", "contract_status": contract_status}

        logger.info(
            "ESCROW OK: contrato concluído para transação %s — prosseguindo com crédito.",
            transacao_id,
        )

    except Exception as _eg:
        logger.error(
            "ESCROW BLOQUEADO (exceção): falha ao verificar contrato para transação %s: %s. "
            "Bloqueando por segurança.",
            transacao_id,
            _eg,
        )
        return {"status": "escrow_bloqueado_excecao", "erro": str(_eg)}

    # Idempotência: se já tem registro de pagamento, ignora
    ja = sb.table("pagamentos_compositores").select("id").eq(
        "transacao_id", transacao_id
    ).limit(1).execute()
    if ja.data:
        logger.info("Wallets já creditadas para transação %s", transacao_id)
        return {"status": "ja_creditado"}

    trans = sb.table("transacoes").select(
        "id, obra_id, valor_cents, stripe_payment_intent, "
        "obras(id, titular_id, publisher_id, gravan_editora_id)"
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
        "plano, status_assinatura, publisher_id"
    ).eq("id", titular_id).single().execute().data or {}
    plano = titular.get("plano", "STARTER")
    status_ass = titular.get("status_assinatura", "inativa")
    if plano == "PRO" and status_ass not in ("ativa", "cancelada", "past_due"):
        plano = "STARTER"
    # publisher_id: lê apenas do perfil do titular (editora parceira real).
    # obras.publisher_id pode ser Gravan (para compositores sem editora), mas
    # Gravan operacional NÃO recebe 10% como editora — somente editoras parceiras
    # reais (perfis com role='publisher' e publisher_id setado no perfil do titular).
    publisher_id = publisher_id_override or titular.get("publisher_id")

    coaut = sb.table("coautorias").select("perfil_id, share_pct").eq(
        "obra_id", t["obra_id"]
    ).execute()
    coautorias_raw = coaut.data or []
    if not coautorias_raw:
        logger.warning(
            "SPLIT: obra %s não possui coautorias cadastradas — 100%% vai ao titular %s. "
            "Verifique se as coautorias foram registradas corretamente na tabela 'coautorias'.",
            t["obra_id"], titular_id,
        )
        coautorias = [{"perfil_id": titular_id, "share_pct": 100}]
    else:
        coautorias = coautorias_raw
        logger.info(
            "SPLIT: obra %s — %d coautoria(s) encontrada(s): %s",
            t["obra_id"], len(coautorias),
            [(c["perfil_id"][:8], c["share_pct"]) for c in coautorias],
        )

    logger.info(
        "SPLIT CALC: transacao=%s, net=%d, plano=%s, publisher_id=%s, coautorias=%d",
        transacao_id, net, plano, publisher_id, len(coautorias),
    )
    split = _calcular_split_sobre_net(net, plano, coautorias, publisher_id=publisher_id)
    logger.info(
        "SPLIT RESULT: plataforma=%d, editora=%d, liquido_autores=%d, payouts=%s",
        split["plataforma_cents"], split.get("editora_cents", 0),
        split["liquido_autores_cents"],
        [(p["perfil_id"][:8], p["valor_cents"], p["share_pct"]) for p in split["payouts"]],
    )

    # Crédito automático da editora vinculada (10%), se aplicável.
    creditados_editora = 0
    edp = split.get("editora_payout")
    if edp and edp["valor_cents"] > 0:
        try:
            sb.rpc("creditar_wallet", {
                "p_perfil_id":    edp["perfil_id"],
                "p_valor_cents":  edp["valor_cents"],
                "p_transacao_id": transacao_id,
            }).execute()
        except Exception as e:
            logger.warning("RPC creditar_wallet (editora) falhou: %s — fallback direto.", e)
            try:
                w = sb.table("wallets").select("saldo_cents").eq(
                    "perfil_id", edp["perfil_id"]
                ).maybe_single().execute()
                saldo_atual = ((w.data if w else None) or {}).get("saldo_cents", 0) or 0
                novo = saldo_atual + edp["valor_cents"]
                # IMPORTANTE: on_conflict="perfil_id" para atualizar wallet
                # existente em vez de tentar inserir e bater na unique.
                sb.table("wallets").upsert(
                    {"perfil_id": edp["perfil_id"], "saldo_cents": novo},
                    on_conflict="perfil_id",
                ).execute()
            except Exception as e2:
                logger.error("Fallback wallet (editora) falhou para %s: %s",
                             edp["perfil_id"], e2)
        try:
            # Editora não é coautora — coautoria_id fica nulo. A coluna
            # precisa permitir NULL no schema (vide migration aplicada).
            sb.table("pagamentos_compositores").insert({
                "perfil_id":    edp["perfil_id"],
                "transacao_id": transacao_id,
                "valor_cents":  edp["valor_cents"],
                "share_pct":    edp["share_pct"],
                "coautoria_id": None,
            }).execute()
            creditados_editora = 1
        except Exception as e:
            logger.warning("Falha ao gravar pagamento da editora: %s", e)

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
                sb.table("wallets").upsert(
                    {"perfil_id": p["perfil_id"], "saldo_cents": novo},
                    on_conflict="perfil_id",
                ).execute()
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
        "status":            "ok",
        "net_cents":         net,
        "plataforma_cents":  split["plataforma_cents"],
        "editora_cents":     split.get("editora_cents", 0),
        "creditados":        creditados,
        "creditados_editora": creditados_editora,
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
    except stripe.StripeError as e:
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
        "obras(id, titular_id, publisher_id, gravan_editora_id)"
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
        "plano, status_assinatura, publisher_id"
    ).eq("id", titular_id).single().execute().data or {}
    plano = titular.get("plano", "STARTER")
    status_ass = titular.get("status_assinatura", "inativa")
    if plano == "PRO" and status_ass not in ("ativa", "cancelada", "past_due"):
        plano = "STARTER"
    # publisher_id: lê apenas do perfil do titular (editora parceira real).
    # Gravan operacional NÃO recebe 10% como editora — somente editoras parceiras.
    publisher_id = titular.get("publisher_id")

    # Coautorias (com fallback 100% titular)
    coaut = sb.table("coautorias").select("perfil_id, share_pct").eq("obra_id", t["obra_id"]).execute()
    coautorias = coaut.data or [{"perfil_id": titular_id, "share_pct": 100}]

    split = _calcular_split_sobre_net(net, plano, coautorias, publisher_id=publisher_id)

    # Editora parceira (real): mesma lógica de "retido/enviado" dos coautores.
    enviados, retidos, falhas = 0, 0, 0
    edp = split.get("editora_payout")
    if edp and edp["valor_cents"] > 0:
        ed_dest = sb.table("perfis").select(
            "stripe_account_id, stripe_charges_enabled"
        ).eq("id", edp["perfil_id"]).single().execute().data or {}
        ed_acc = ed_dest.get("stripe_account_id")
        ed_pode = ed_acc and ed_dest.get("stripe_charges_enabled")
        ed_row = {
            "transacao_id":      transacao_id,
            "perfil_id":         edp["perfil_id"],
            "valor_cents":       edp["valor_cents"],
            "share_pct":         edp["share_pct"],
            "stripe_account_id": ed_acc,
            "status":            "retido" if not ed_pode else "pendente",
            "metadata":          {
                "net_cents_base": net,
                "plano_titular":  plano,
                "papel":          "editora",
            },
        }
        if not ed_pode:
            sb.table("repasses").insert(ed_row).execute()
            retidos += 1
        else:
            try:
                tr = stripe.Transfer.create(
                    amount=edp["valor_cents"],
                    currency="brl",
                    destination=ed_acc,
                    transfer_group=f"OBRA_{t['obra_id']}_TRANS_{transacao_id}",
                    metadata={
                        "transacao_id": transacao_id,
                        "perfil_id":    edp["perfil_id"],
                        "obra_id":      t["obra_id"],
                        "papel":        "editora",
                    },
                    idempotency_key=f"transfer_editora_{transacao_id}_{edp['perfil_id']}",
                )
                ed_row["stripe_transfer_id"] = tr.id
                ed_row["status"] = "enviado"
                ed_row["enviado_at"] = datetime.utcnow().isoformat() + "Z"
                sb.table("repasses").insert(ed_row).execute()
                enviados += 1
            except stripe.StripeError as e:
                ed_row["status"]   = "falhou"
                ed_row["erro_msg"] = (e.user_message or str(e))[:500]
                sb.table("repasses").insert(ed_row).execute()
                falhas += 1
                logger.error("Falha no Transfer EDITORA para %s: %s", edp["perfil_id"], e)

    # Cria registros + dispara transfers para coautores
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
                "papel":          "compositor",
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
            repasse_row["enviado_at"] = datetime.utcnow().isoformat() + "Z"
            sb.table("repasses").insert(repasse_row).execute()
            enviados += 1
        except stripe.StripeError as e:
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
                "enviado_at":         datetime.utcnow().isoformat() + "Z",
                "liberado_at":        datetime.utcnow().isoformat() + "Z",
            }).eq("id", rep["id"]).execute()
            enviados += 1
        except stripe.StripeError as e:
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
        except stripe.StripeError as e:
            logger.error("Falha ao reverter transfer %s: %s", r["stripe_transfer_id"], e)

    return {"status": "ok", "revertidos": revertidos}
