"""
Service: criação e liberação de repasses (Transfers Stripe Connect).

Regra B confirmada pelo usuário:
  - Se o autor NÃO tiver conta Connect ativa, o valor fica RETIDO.
  - Quando ele completa o onboarding (webhook account.updated), liberamos.

Taxas Stripe são deduzidas ANTES do split (item 9): usamos o `net` do
balance_transaction como base de cálculo, então todos pagam proporcionalmente.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REGRA DE ESCROW — ACIMA DE TODAS AS OUTRAS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
NENHUM saldo é creditado na carteira de ninguém enquanto o contrato
de licenciamento da transação estiver com status != 'concluído'.

A função _escrow_guard() é o ponto único de verificação e DEVE ser a
primeira chamada em QUALQUER função que credite wallets ou dispare
Stripe Transfers. Toda nova função de crédito futura deve chamar
_escrow_guard() antes de qualquer outra lógica.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
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


# ══════════════════════════════════════════════════════════════
# GUARDA CENTRAL DE ESCROW
# ══════════════════════════════════════════════════════════════
# UUID da Gravan operacional (editora institucional bilateral). Auto-assina por design.
_GRAVAN_EDITORA_UUID = "e96bd8af-dfb8-4bf1-9ba5-7746207269cd"


def _escrow_guard(transacao_id: str, sb, caller: str = "desconhecido") -> bool:
    """
    Verifica se o contrato de licenciamento vinculado à transação está
    com status 'concluído' (todas as partes assinaram) E se cada signer
    humano tem assinatura registrada via HTTP (ip_hash preenchido).

    RETORNA:
      True  → contrato concluído + todas as assinaturas humanas validadas.
      False → contrato não concluído OU alguma assinatura humana ausente.

    REGRA ABSOLUTA: esta função DEVE ser a primeira chamada em qualquer
    caminho de código que credite wallets ou dispare Stripe Transfers.
    Em caso de dúvida, BLOQUEIA (fail-safe).

    DEFESA EM PROFUNDIDADE: além de checar o status do contrato, validamos
    diretamente que cada signer humano (autor, coautor, editora_detentora
    NÃO-Gravan) tem signed=True E ip_hash preenchido — marca de que a
    assinatura veio de uma chamada HTTP real à rota /aceitar (que registra
    sempre o ip_hash via hash_ip(remote_addr)). Signatários que assinam
    automaticamente por design ficam isentos:
      • Gravan (editora_detentora bilateral) — autoassinatura institucional.
      • Comprador (interprete) — aceite eletrônico via pagamento.
    """
    try:
        row = sb.table("contracts").select("id, status").eq(
            "transacao_id", transacao_id
        ).limit(1).execute()

        if not row.data:
            logger.error(
                "ESCROW BLOQUEADO [%s]: transação '%s' não possui contrato vinculado. "
                "Nenhuma carteira será creditada. (Possível chamada prematura antes de "
                "gerar_contrato_licenciamento ser concluído.)",
                caller, transacao_id,
            )
            return False

        status = row.data[0].get("status", "")
        contract_id = row.data[0].get("id", "")

        if status not in ("concluído", "concluido"):
            logger.error(
                "ESCROW BLOQUEADO [%s]: contrato %s da transação '%s' está '%s' "
                "(necessário: 'concluído'). Nenhuma carteira será creditada enquanto "
                "o contrato estiver 'Aguardando assinaturas'.",
                caller, contract_id, transacao_id, status,
            )
            return False

        # ── TRAVA EXTRA: assinatura humana real por papel ──────────────
        # Mesmo que status='concluído', validamos diretamente os signers
        # para impedir que o status seja contornado por edição manual no
        # banco ou caminho de código que ignore aceitar_contrato().
        signers = sb.table("contract_signers").select(
            "user_id, role, signed, ip_hash"
        ).eq("contract_id", contract_id).execute().data or []

        humanos = [
            s for s in signers
            if s.get("role") in ("autor", "coautor", "editora_detentora", "editora_agregadora")
            and s.get("user_id") != _GRAVAN_EDITORA_UUID  # Gravan: autoassinatura institucional
        ]

        if not humanos:
            logger.error(
                "ESCROW BLOQUEADO [%s]: contrato %s da transação '%s' está 'concluído' "
                "mas NÃO possui nenhum signer humano (autor/coautor/editora) cadastrado. "
                "Anomalia grave — bloqueando por segurança.",
                caller, contract_id, transacao_id,
            )
            return False

        nao_assinaram = [
            s for s in humanos
            if not (s.get("signed") and s.get("ip_hash"))
        ]
        if nao_assinaram:
            logger.error(
                "ESCROW BLOQUEADO [%s] (HUMAN SIGNATURE CHECK): contrato %s da "
                "transação '%s' está 'concluído', mas %d signer(s) humano(s) "
                "não possuem assinatura via HTTP (signed + ip_hash): %s. "
                "Wallets NÃO serão creditadas.",
                caller, contract_id, transacao_id, len(nao_assinaram),
                [(s.get("role"), (s.get("user_id") or "")[:8],
                  "signed" if s.get("signed") else "unsigned",
                  "ip" if s.get("ip_hash") else "no-ip")
                 for s in nao_assinaram],
            )
            try:
                sb.table("contract_events").insert({
                    "contract_id": contract_id,
                    "event_type":  "escrow_blocked_human_check",
                    "payload": {
                        "caller": caller,
                        "transacao_id": transacao_id,
                        "missing": [
                            {"role": s.get("role"),
                             "user_id_prefix": (s.get("user_id") or "")[:12],
                             "signed": bool(s.get("signed")),
                             "has_ip_hash": bool(s.get("ip_hash"))}
                            for s in nao_assinaram
                        ],
                    },
                }).execute()
            except Exception:
                pass
            return False

        logger.info(
            "ESCROW LIBERADO [%s]: contrato %s da transação '%s' está '%s' e "
            "todos os %d signer(s) humano(s) assinaram via HTTP (ip_hash ok). "
            "Prosseguindo com crédito de carteiras.",
            caller, contract_id, transacao_id, status, len(humanos),
        )
        return True

    except Exception as exc:
        logger.error(
            "ESCROW BLOQUEADO [%s]: exceção ao verificar contrato da transação '%s': %s. "
            "Bloqueando por segurança (fail-safe).",
            caller, transacao_id, exc,
        )
        return False


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

    ESCROW: usa _escrow_guard() — regra absoluta acima de tudo.
    Nenhuma carteira é creditada enquanto o contrato estiver pendente.
    """
    sb = get_supabase()

    # ── GUARDA CENTRAL DE ESCROW (primeira instrução, sem exceção) ──────────
    if not _escrow_guard(transacao_id, sb, caller="creditar_wallets_por_transacao"):
        return {"status": "escrow_bloqueado"}

    # Idempotência GRANULAR: ao invés de bailar fora se QUALQUER pagamento
    # existir para a transação, listamos todos os perfis_id já pagos e
    # creditamos somente o que estiver faltando. Isso permite recuperação
    # automática quando uma execução anterior pagou os autores mas falhou
    # (silenciosamente) na editora — bug histórico que deixou editoras sem
    # receber 10%. Cada perfil só é creditado UMA vez, mas a função pode
    # rodar N vezes para a mesma transação sem perder pagamentos faltantes.
    ja_pagos = sb.table("pagamentos_compositores").select("perfil_id").eq(
        "transacao_id", transacao_id
    ).execute()
    perfis_ja_pagos = {r["perfil_id"] for r in (ja_pagos.data or []) if r.get("perfil_id")}
    if perfis_ja_pagos:
        logger.info(
            "Idempotência granular: transação %s já tem pagamento para %d perfil(is): %s. "
            "Creditarei apenas perfis faltantes.",
            transacao_id, len(perfis_ja_pagos),
            [p[:8] for p in perfis_ja_pagos],
        )

    trans = sb.table("transacoes").select(
        "id, obra_id, valor_cents, stripe_payment_intent, "
        "obras!transacoes_obra_id_fkey(id, titular_id, publisher_id, gravan_editora_id)"
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
    # publisher_id: fonte de verdade é obras.publisher_id (define a relação editorial
    # no momento da criação da obra). Gravan operacional é excluída — ela gerencia a
    # plataforma mas não toma 10% como editora parceira real.
    #
    # Ordem de resolução:
    #   1. publisher_id_override (passado pelo caller, e.g. backfill manual)
    #   2. obras.publisher_id  — vínculo editorial no momento da criação da obra
    #   3. perfis.publisher_id — agregação atual do compositor (fallback)
    # Gravan é excluída em qualquer caso.
    _GRAVAN_UUID = "e96bd8af-dfb8-4bf1-9ba5-7746207269cd"
    obra_publisher  = obra.get("publisher_id")
    perfil_publisher = titular.get("publisher_id")

    if publisher_id_override:
        publisher_id = publisher_id_override
    elif obra_publisher and obra_publisher != _GRAVAN_UUID:
        publisher_id = obra_publisher          # editorial partner set at obra creation
    elif perfil_publisher and perfil_publisher != _GRAVAN_UUID:
        publisher_id = perfil_publisher        # current aggregation state (fallback)
    else:
        publisher_id = None                    # no external publisher — Gravan doesn't get 10%

    logger.info(
        "SPLIT PUBLISHER RESOLVE: obra_pub=%s perfil_pub=%s override=%s resolved=%s",
        (obra_publisher or "")[:12],
        (perfil_publisher or "")[:12],
        publisher_id_override,
        (publisher_id or "none"),
    )

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

    # Helper: localiza o contract_id desta transação (para registrar eventos
    # de erro auditáveis em contract_events).
    def _contract_id_para_evento() -> str | None:
        try:
            r = sb.table("contracts").select("id").eq(
                "transacao_id", transacao_id
            ).limit(1).execute()
            return (r.data or [{}])[0].get("id")
        except Exception:
            return None

    def _registrar_falha_credito(perfil_id: str, papel: str, etapa: str, erro: str) -> None:
        """Registra falha de crédito em contract_events para alertar a operação.
        Substitui o antigo 'logger.warning + segue a vida' que mascarava bugs
        como o do split da editora (transação 3e889470)."""
        cid = _contract_id_para_evento()
        if not cid:
            return
        try:
            sb.table("contract_events").insert({
                "contract_id": cid,
                "event_type":  "credito_falhou",
                "payload": {
                    "transacao_id": transacao_id,
                    "perfil_id":    perfil_id,
                    "papel":        papel,
                    "etapa":        etapa,
                    "erro":         (erro or "")[:500],
                },
            }).execute()
        except Exception:
            pass

    def _creditar_wallet(perfil_id: str, valor_cents: int, papel: str) -> bool:
        """Tenta RPC; se falhar, faz upsert direto. Retorna True se OK."""
        try:
            sb.rpc("creditar_wallet", {
                "p_perfil_id":    perfil_id,
                "p_valor_cents":  valor_cents,
                "p_transacao_id": transacao_id,
            }).execute()
            return True
        except Exception as e:
            logger.warning("RPC creditar_wallet (%s) falhou: %s — tentando fallback.", papel, e)
            try:
                w = sb.table("wallets").select("saldo_cents").eq(
                    "perfil_id", perfil_id
                ).maybe_single().execute()
                saldo_atual = ((w.data if w else None) or {}).get("saldo_cents", 0) or 0
                novo = saldo_atual + valor_cents
                sb.table("wallets").upsert(
                    {"perfil_id": perfil_id, "saldo_cents": novo},
                    on_conflict="perfil_id",
                ).execute()
                return True
            except Exception as e2:
                logger.error("Fallback wallet (%s) falhou para perfil %s: %s — RPC erro: %s",
                             papel, perfil_id, e2, e)
                _registrar_falha_credito(perfil_id, papel, "wallet",
                                         f"rpc={e}; fallback={e2}")
                return False

    # Crédito automático da editora vinculada (10%), se aplicável.
    creditados_editora = 0
    edp = split.get("editora_payout")
    if edp and edp["valor_cents"] > 0:
        if edp["perfil_id"] in perfis_ja_pagos:
            logger.info(
                "Editora %s já tem pagamento para transação %s — pulando (idempotência granular).",
                edp["perfil_id"][:8], transacao_id,
            )
        else:
            wallet_ok = _creditar_wallet(edp["perfil_id"], edp["valor_cents"], "editora")
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
                logger.info(
                    "EDITORA CREDITADA: perfil=%s, valor=%d cents, transacao=%s, wallet_ok=%s",
                    edp["perfil_id"][:8], edp["valor_cents"], transacao_id, wallet_ok,
                )
            except Exception as e:
                logger.error(
                    "FALHA AO GRAVAR pagamento da editora (perfil=%s, transacao=%s): %s. "
                    "Wallet credit foi %s. Registrando em contract_events para reconciliação.",
                    edp["perfil_id"], transacao_id, e,
                    "OK" if wallet_ok else "TAMBÉM FALHOU",
                )
                _registrar_falha_credito(edp["perfil_id"], "editora",
                                         "pagamentos_compositores", str(e))

    creditados = 0
    for p in split["payouts"]:
        if p["valor_cents"] <= 0:
            continue
        if p["perfil_id"] in perfis_ja_pagos:
            logger.info(
                "Autor/coautor %s já tem pagamento para transação %s — pulando.",
                p["perfil_id"][:8], transacao_id,
            )
            continue

        wallet_ok = _creditar_wallet(p["perfil_id"], p["valor_cents"], "autor")
        if not wallet_ok:
            continue  # já logado e registrado em contract_events

        # Registra histórico de pagamento
        try:
            sb.table("pagamentos_compositores").insert({
                "perfil_id":    p["perfil_id"],
                "transacao_id": transacao_id,
                "valor_cents":  p["valor_cents"],
                "share_pct":    p["share_pct"],
            }).execute()
        except Exception as e:
            logger.error(
                "FALHA AO GRAVAR pagamentos_compositores (autor perfil=%s, transacao=%s): %s. "
                "Wallet já foi creditada. Registrando em contract_events para reconciliação.",
                p["perfil_id"], transacao_id, e,
            )
            _registrar_falha_credito(p["perfil_id"], "autor",
                                     "pagamentos_compositores", str(e))
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

    ESCROW: usa _escrow_guard() — regra absoluta acima de tudo.
    Nenhum Transfer Stripe é disparado enquanto o contrato estiver pendente.
    """
    _ensure_key()
    sb = get_supabase()

    # ── GUARDA CENTRAL DE ESCROW (primeira instrução, sem exceção) ──────────
    if not _escrow_guard(transacao_id, sb, caller="gerar_repasses_para_transacao"):
        return {"status": "escrow_bloqueado"}

    # Já gerado?
    existing = sb.table("repasses").select("id").eq("transacao_id", transacao_id).limit(1).execute()
    if existing.data:
        logger.info("Repasses já existem para transação %s — ignorando.", transacao_id)
        return {"status": "ja_existia", "qtd": len(existing.data)}

    trans = sb.table("transacoes").select(
        "id, obra_id, valor_cents, stripe_payment_intent, "
        "obras!transacoes_obra_id_fkey(id, titular_id, publisher_id, gravan_editora_id)"
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
