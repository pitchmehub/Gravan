"""
Serviço: Ofertas de Licenciamento p/ obras editadas por terceira editora.

Fluxo:
  1. Comprador licencia uma obra com `obra_editada_terceiros=true`.
  2. Cria-se uma `ofertas_licenciamento` (status=aguardando_pagamento) e um
     PaymentIntent Stripe com `capture_method='manual'` (hold no cartão).
  3. Após confirmação do pagamento (webhook `payment_intent.amount_capturable_updated`
     ou `payment_intent.succeeded` em manual capture), status vira
     `aguardando_editora` e enviamos e-mail para a editora terceira com link
     de cadastro contendo o `registration_token`.
  4. Deadline = 72 horas úteis (BRT, 10–18h, dias úteis BR).
  5. Editora se cadastra → vincula `editora_terceira_id` → status `editora_cadastrada`.
  6. Geramos contrato trilateral (autor + Gravan + comprador + editora terceira).
  7. Quando todos assinam, capturamos o pagamento, status `concluida`.
  8. Se o deadline expirar antes da assinatura: `cancel` no PaymentIntent
     (libera o hold) → status `expirada`/`reembolsada` e e-mail ao comprador.
  9. Reminders 48h e 24h antes do deadline.
"""
from __future__ import annotations

import os
import secrets
import logging
from datetime import datetime, timezone
from typing import Optional

import stripe

from db.supabase_client import get_supabase
from utils.business_hours import (
    add_business_hours, business_hours_remaining, BRT,
)
from services.email_service import (
    send_email,
    render_oferta_editora_email,
    render_oferta_reminder_email,
    render_oferta_expirada_comprador_email,
    render_oferta_expirada_editora_email,
    render_oferta_concluida_email,
    render_oferta_notificacao_compositor_email,
    render_oferta_lembrete_compositor_email,
    render_oferta_expirada_compositor_email,
    render_oferta_concluida_compositor_email,
    render_oferta_concluida_editora_terceira_email,
)

log = logging.getLogger("gravan.ofertas")

stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173")

DEADLINE_HOURS = 72  # horas COMERCIAIS


# ─────────────────────────── helpers ───────────────────────────

def _gen_token() -> str:
    return secrets.token_urlsafe(32)


def _link_aceitar_oferta(token: str) -> str:
    return f"{FRONTEND_URL}/editora/aceitar-oferta/{token}"


def _moeda(cents: int) -> str:
    s = f"R$ {(cents/100):,.2f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def _get_compositores(obra_id: str) -> list[dict]:
    """Retorna lista de {nome, email, papel} para compositor titular e coautores da obra."""
    sb = get_supabase()
    obra = sb.table("obras").select("titular_id").eq("id", obra_id).maybe_single().execute()
    obra = (obra.data if obra else None) or {}
    titular_id = obra.get("titular_id")

    autores_rows = sb.table("obra_autores").select("perfil_id, is_titular").eq(
        "obra_id", obra_id
    ).execute().data or []

    perfil_ids = [r["perfil_id"] for r in autores_rows if r.get("perfil_id")]
    if titular_id and titular_id not in perfil_ids:
        perfil_ids.append(titular_id)
    if not perfil_ids:
        return []

    perfis = sb.table("perfis").select("id, nome, nome_completo, email").in_(
        "id", perfil_ids
    ).execute().data or []

    resultado = []
    vistos: set[str] = set()
    for p in perfis:
        email = (p.get("email") or "").strip().lower()
        if not email or email in vistos:
            continue
        papel = "compositor" if p.get("id") == titular_id else "coautor"
        resultado.append({
            "nome":  p.get("nome_completo") or p.get("nome") or "",
            "email": email,
            "papel": papel,
        })
        vistos.add(email)
    return resultado


# ─────────────────────────── criação ───────────────────────────

def criar_oferta(
    obra_id: str,
    comprador_id: str,
    metodo: str = "credito",
) -> dict:
    """
    Cria uma oferta + Checkout Session em manual-capture.
    Devolve dict com `checkout_url`, `session_id`, `oferta_id`.
    """
    if not stripe.api_key:
        raise RuntimeError("Stripe não configurado: STRIPE_SECRET_KEY ausente.")

    sb = get_supabase()

    obra = sb.table("obras").select(
        "id, nome, preco_cents, status, titular_id,"
        " obra_editada_terceiros, editora_terceira_nome,"
        " editora_terceira_email, editora_terceira_telefone, editora_terceira_id"
    ).eq("id", obra_id).single().execute().data
    if not obra:
        raise ValueError("Obra não encontrada.")
    if obra.get("status") != "publicada":
        raise ValueError("Obra não está publicada.")
    if not obra.get("obra_editada_terceiros"):
        raise ValueError("Esta obra não está marcada como editada por terceiros.")
    if obra.get("titular_id") == comprador_id:
        raise ValueError("Você não pode licenciar uma obra de sua própria autoria.")
    if not obra.get("editora_terceira_email"):
        raise ValueError("Obra sem dados da editora terceira; contate o suporte.")

    comprador = sb.table("perfis").select("nome, email").eq("id", comprador_id).single().execute().data or {}

    token = _gen_token()
    deadline = add_business_hours(datetime.now(timezone.utc), DEADLINE_HOURS)

    # Cria a oferta antes de bater no Stripe para ter id estável
    novo = sb.table("ofertas_licenciamento").insert({
        "obra_id":                  obra_id,
        "comprador_id":             comprador_id,
        "valor_cents":              obra["preco_cents"],
        "editora_terceira_nome":    obra["editora_terceira_nome"],
        "editora_terceira_email":   obra["editora_terceira_email"].lower().strip(),
        "editora_terceira_telefone": obra.get("editora_terceira_telefone"),
        "editora_terceira_id":      obra.get("editora_terceira_id"),
        "registration_token":       token,
        "status":                   "aguardando_pagamento",
        "deadline_at":              deadline.isoformat(),
    }).execute().data[0]

    # Checkout em manual capture (hold no cartão)
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="payment",
            line_items=[{
                "price_data": {
                    "currency": "brl",
                    "product_data": {
                        "name": f"Oferta de Licença: {obra['nome']}",
                        "description": "Valor retido até a assinatura da editora detentora dos direitos.",
                    },
                    "unit_amount": obra["preco_cents"],
                },
                "quantity": 1,
            }],
            customer_email=comprador.get("email"),
            payment_intent_data={
                "capture_method": "manual",
                "metadata": {
                    "tipo":        "oferta_licenciamento_terceiros",
                    "oferta_id":   novo["id"],
                    "obra_id":     obra_id,
                    "comprador_id": comprador_id,
                },
            },
            success_url=f"{FRONTEND_URL}/ofertas/sucesso?oferta_id={novo['id']}",
            cancel_url=f"{FRONTEND_URL}/ofertas/cancelado?oferta_id={novo['id']}",
            metadata={
                "tipo":      "oferta_licenciamento_terceiros",
                "oferta_id": novo["id"],
            },
        )
    except stripe.StripeError as e:
        sb.table("ofertas_licenciamento").update({
            "status": "cancelada",
            "cancelada_em": datetime.now(timezone.utc).isoformat(),
        }).eq("id", novo["id"]).execute()
        raise RuntimeError(f"Erro Stripe: {e.user_message or str(e)}")

    sb.table("ofertas_licenciamento").update({
        "stripe_checkout_session_id": session.id,
    }).eq("id", novo["id"]).execute()

    return {
        "oferta_id":    novo["id"],
        "checkout_url": session.url,
        "session_id":   session.id,
        "deadline_at":  deadline.isoformat(),
    }


# ───────────────── confirmação de pagamento (webhook) ─────────────────

def on_payment_authorized(session_id: str, payment_intent_id: str) -> Optional[dict]:
    """
    Chamado quando o Checkout completa em manual-capture: o cartão está
    autorizado mas ainda não capturado. Move a oferta para `aguardando_editora`
    e dispara o e-mail para a editora terceira.
    """
    sb = get_supabase()
    of = sb.table("ofertas_licenciamento").select("*").eq(
        "stripe_checkout_session_id", session_id
    ).single().execute().data
    if not of:
        log.warning("Oferta não encontrada para session_id=%s", session_id)
        return None
    if of["status"] != "aguardando_pagamento":
        return of  # idempotente

    sb.table("ofertas_licenciamento").update({
        "status":                   "aguardando_editora",
        "stripe_payment_intent_id": payment_intent_id,
        "pago_em":                  datetime.now(timezone.utc).isoformat(),
    }).eq("id", of["id"]).execute()

    obra = sb.table("obras").select("nome, titular_id").eq("id", of["obra_id"]).single().execute().data or {}
    comprador = sb.table("perfis").select("nome, email").eq("id", of["comprador_id"]).single().execute().data or {}

    deadline_brt = datetime.fromisoformat(of["deadline_at"].replace("Z","+00:00")).astimezone(BRT)
    deadline_str = deadline_brt.strftime("%d/%m/%Y às %H:%M (BRT)")

    # Se a editora terceira já é cadastrada na plataforma → notificação interna.
    # E-mail também é enviado, como canal redundante (a editora não pode perder o prazo).
    if of.get("editora_terceira_id"):
        try:
            from services.notificacoes import notify
            notify(
                perfil_id=of["editora_terceira_id"],
                tipo="oferta",
                titulo=f"Nova oferta de licença: \"{obra.get('nome','obra')}\"",
                mensagem=(
                    f"O intérprete {comprador.get('nome') or 'um cliente'} fez uma oferta "
                    f"de {_moeda(of['valor_cents'])} para licenciar a obra "
                    f"\"{obra.get('nome','—')}\". Você tem até {deadline_str} para "
                    f"aceitar e assinar o contrato trilateral."
                ),
                link="/publisher/dashboard",
                payload={
                    "oferta_id":   of["id"],
                    "obra_id":     of["obra_id"],
                    "valor_cents": of["valor_cents"],
                    "deadline_at": of["deadline_at"],
                },
            )
            log.info("Notificação interna enviada para editora cadastrada %s",
                     of["editora_terceira_id"])
        except Exception as e:
            log.exception("Falha ao notificar editora cadastrada: %s", e)

    html, text = render_oferta_editora_email(
        nome_editora=of["editora_terceira_nome"],
        nome_obra=obra.get("nome", "—"),
        valor_brl=_moeda(of["valor_cents"]),
        nome_comprador=comprador.get("nome") or "Intérprete",
        deadline_str=deadline_str,
        link=_link_aceitar_oferta(of["registration_token"]),
    )
    send_email(of["editora_terceira_email"],
               f"Gravan — Pedido de licenciamento de \"{obra.get('nome','obra musical')}\"",
               html, text)

    # Notifica compositor e coautores da obra sobre a oferta recebida
    try:
        for c in _get_compositores(of["obra_id"]):
            h, t = render_oferta_notificacao_compositor_email(
                nome=c["nome"],
                nome_obra=obra.get("nome", "—"),
                valor_brl=_moeda(of["valor_cents"]),
                nome_comprador=comprador.get("nome") or "Intérprete",
                deadline_str=deadline_str,
            )
            send_email(c["email"],
                       f"Gravan — Oferta de licenciamento em andamento: \"{obra.get('nome','—')}\"",
                       h, t)
    except Exception as e:
        log.warning("Falha ao notificar compositores sobre oferta %s: %s", of.get("id"), e)

    # Notifica o compositor titular da obra sobre a oferta de licenciamento
    if obra.get("titular_id"):
        try:
            from services.notificacoes import notify
            notify(
                perfil_id=obra["titular_id"],
                tipo="oferta",
                titulo=f"Nova oferta de licença: \"{obra.get('nome','sua obra')}\"",
                mensagem=(
                    f"{comprador.get('nome') or 'Um intérprete'} fez uma oferta de licença de "
                    f"{_moeda(of['valor_cents'])} para \"{obra.get('nome','—')}\". "
                    f"Aguardando aprovação da editora até {deadline_str}."
                ),
                link="/dashboard",
                payload={
                    "oferta_id":   of["id"],
                    "obra_id":     of["obra_id"],
                    "valor_cents": of["valor_cents"],
                    "deadline_at": of["deadline_at"],
                },
            )
        except Exception as e:
            log.warning("Falha ao notificar compositor da oferta de licenciamento %s: %s", of.get("id"), e)

    return sb.table("ofertas_licenciamento").select("*").eq("id", of["id"]).single().execute().data


# ─────────────── editora aceita (cadastra-se) via token ───────────────

def vincular_editora_por_token(token: str, publisher_id: str) -> dict:
    """
    Após a editora terceira completar o cadastro PJ, vincula o id ao perfil
    e à(s) oferta(s)/obra(s) correspondente(s). Retorna a oferta atualizada.
    """
    sb = get_supabase()
    of = sb.table("ofertas_licenciamento").select("*").eq(
        "registration_token", token
    ).single().execute().data
    if not of:
        raise ValueError("Oferta não encontrada para este token.")
    if of["status"] not in ("aguardando_editora",):
        raise ValueError(f"Oferta em status '{of['status']}' — não é mais possível aceitar.")
    if business_hours_remaining(
        datetime.fromisoformat(of["deadline_at"].replace("Z","+00:00"))
    ) <= 0:
        raise ValueError("Prazo esgotado. A oferta foi (ou será) estornada ao comprador.")

    # Verifica se o perfil é mesmo publisher
    p = sb.table("perfis").select("role, email, razao_social").eq(
        "id", publisher_id
    ).single().execute().data or {}
    if p.get("role") != "publisher" or not p.get("razao_social"):
        raise ValueError("Cadastro de editora ainda não concluído.")

    # Vincula
    sb.table("ofertas_licenciamento").update({
        "editora_terceira_id":   publisher_id,
        "status":                "editora_cadastrada",
        "editora_cadastrada_em": datetime.now(timezone.utc).isoformat(),
    }).eq("id", of["id"]).execute()

    sb.table("obras").update({
        "editora_terceira_id": publisher_id,
    }).eq("id", of["obra_id"]).execute()

    # Dispara geração do contrato trilateral
    try:
        from services.contrato_licenciamento import gerar_contrato_trilateral
        contrato = gerar_contrato_trilateral(of["id"])
        if contrato:
            sb.table("ofertas_licenciamento").update({
                "status":      "em_assinatura",
                "contrato_id": contrato["id"],
            }).eq("id", of["id"]).execute()
    except Exception as e:
        log.exception("Falha ao gerar contrato trilateral: %s", e)

    return sb.table("ofertas_licenciamento").select("*").eq("id", of["id"]).single().execute().data


# ─────────────── conclusão (após todas assinaturas) ───────────────

def on_contrato_concluido(contract_id: str) -> Optional[dict]:
    """
    Chamado quando o contrato trilateral é totalmente assinado.
    Captura o PaymentIntent (libera o valor), cria registro em `transacoes`
    e CREDITA AUTOMATICAMENTE as wallets do split:
      - 25% → plataforma (taxa única)
      - 10% → editora terceira (que aceitou a oferta)
      - resto → autor titular + coautores conforme `share_pct`
    Idempotente: só credita uma vez (proteção via `pagamentos_compositores`).
    """
    sb = get_supabase()
    of = sb.table("ofertas_licenciamento").select("*").eq(
        "contrato_id", contract_id
    ).single().execute().data
    if not of:
        return None
    if of["status"] == "concluida":
        return of

    pi_id = of.get("stripe_payment_intent_id")
    if pi_id:
        try:
            stripe.PaymentIntent.capture(pi_id)
        except stripe.StripeError as e:
            # idempotência: se já foi capturada antes, segue em frente
            msg = str(e).lower()
            if "already" not in msg and "already_captured" not in msg:
                log.error("Falha ao capturar PI %s: %s", pi_id, e)
                return of

    sb.table("ofertas_licenciamento").update({
        "status":       "concluida",
        "concluida_em": datetime.now(timezone.utc).isoformat(),
    }).eq("id", of["id"]).execute()

    # ── Cria transação + credita wallets (split automático) ────────
    transacao_id = of.get("transacao_id")
    try:
        if not transacao_id and pi_id:
            # Reaproveita transação existente (caso webhook tenha disparado 2x)
            existente = sb.table("transacoes").select("id").eq(
                "stripe_payment_intent", pi_id
            ).limit(1).execute()
            if existente.data:
                transacao_id = existente.data[0]["id"]

        if not transacao_id:
            ins = sb.table("transacoes").insert({
                "obra_id":               of["obra_id"],
                "comprador_id":          of["comprador_id"],
                "valor_cents":           of["valor_cents"],
                "metodo":                "credito",
                "provedor":              "stripe",
                "status":                "confirmada",
                "stripe_payment_intent": pi_id,
                "confirmed_at":          datetime.now(timezone.utc).isoformat(),
                "metadata": {
                    "origem":     "oferta_licenciamento_terceiros",
                    "oferta_id":  of["id"],
                    "contrato_id": contract_id,
                },
            }).execute()
            transacao_id = ins.data[0]["id"] if ins.data else None
            if transacao_id:
                sb.table("ofertas_licenciamento").update({
                    "transacao_id": transacao_id,
                }).eq("id", of["id"]).execute()
                # ESCROW: vincula a transação ao contrato (contracts.transacao_id)
                # para que o guard em creditar_wallets_por_transacao consiga
                # verificar que o contrato está 'concluído' antes de creditar.
                if contract_id:
                    try:
                        sb.table("contracts").update({
                            "transacao_id": transacao_id,
                        }).eq("id", contract_id).is_("transacao_id", "null").execute()
                    except Exception as _tle:
                        log.warning(
                            "Não foi possível vincular transacao_id ao contrato %s: %s",
                            contract_id, _tle,
                        )
    except Exception as e:
        log.exception("Falha ao criar transação para oferta %s: %s", of["id"], e)

    # Credita as wallets reusando o pipeline padrão (10% editora terceira,
    # plataforma conforme plano do titular, resto entre coautores).
    if transacao_id and of.get("editora_terceira_id"):
        try:
            from services.repasses import creditar_wallets_por_transacao
            resultado = creditar_wallets_por_transacao(
                transacao_id,
                publisher_id_override=of["editora_terceira_id"],
            )
            log.info("Wallets creditadas oferta %s: %s", of["id"], resultado)
        except Exception as e:
            log.exception("Falha ao creditar wallets da oferta %s: %s", of["id"], e)

    # ── Notifica autor titular + comunicação por e-mail ──────────────
    obra = sb.table("obras").select("nome, titular_id").eq("id", of["obra_id"]).single().execute().data or {}
    comprador = sb.table("perfis").select("nome, email").eq("id", of["comprador_id"]).single().execute().data or {}

    if obra.get("titular_id"):
        try:
            from services.notificacoes import notify
            notify(
                perfil_id=obra["titular_id"],
                tipo="compra",
                titulo=f"Licença concluída: \"{obra.get('nome','sua obra')}\"",
                mensagem=(
                    f"O contrato trilateral de \"{obra.get('nome','—')}\" foi assinado "
                    f"por todas as partes. Sua parte do valor ({_moeda(of['valor_cents'])}) "
                    f"já foi creditada na sua carteira."
                ),
                link="/dashboard",
                payload={
                    "oferta_id":    of["id"],
                    "obra_id":      of["obra_id"],
                    "transacao_id": transacao_id,
                    "valor_cents":  of["valor_cents"],
                },
            )
        except Exception as e:
            log.warning("Falha ao notificar titular sobre conclusão da oferta %s: %s", of["id"], e)

    if of.get("editora_terceira_id"):
        try:
            from services.notificacoes import notify
            notify(
                perfil_id=of["editora_terceira_id"],
                tipo="compra",
                titulo=f"Você recebeu uma comissão: \"{obra.get('nome','obra')}\"",
                mensagem=(
                    f"Sua comissão de 10% sobre \"{obra.get('nome','—')}\" "
                    f"({_moeda(int(of['valor_cents'] * 0.10))} aprox.) já foi "
                    f"creditada na sua carteira. Você pode sacar quando quiser."
                ),
                link="/publisher/dashboard",
                payload={
                    "oferta_id":    of["id"],
                    "obra_id":      of["obra_id"],
                    "transacao_id": transacao_id,
                },
            )
        except Exception as e:
            log.warning("Falha ao notificar editora terceira sobre conclusão da oferta %s: %s", of["id"], e)

    nome_obra = obra.get("nome", "—")
    valor_brl = _moeda(of["valor_cents"])

    if comprador.get("email"):
        h, t = render_oferta_concluida_email(comprador.get("nome") or "Intérprete",
                                             nome_obra, valor_brl)
        send_email(comprador["email"], "Gravan — Licença concluída", h, t)

    # Notifica compositor e coautores: licença concluída + saldo creditado
    try:
        for c in _get_compositores(of["obra_id"]):
            hc, tc = render_oferta_concluida_compositor_email(
                nome=c["nome"],
                nome_obra=nome_obra,
                valor_brl=valor_brl,
            )
            send_email(c["email"],
                       f"Gravan — Licenciamento concluído: \"{nome_obra}\"",
                       hc, tc)
    except Exception as e:
        log.warning("Falha ao notificar compositores sobre conclusão %s: %s", of.get("id"), e)

    # Notifica a editora terceira sobre a comissão creditada
    if of.get("editora_terceira_email"):
        try:
            comissao_brl = _moeda(int(of["valor_cents"] * 0.10))
            he, te = render_oferta_concluida_editora_terceira_email(
                nome_editora=of["editora_terceira_nome"] or "Editora",
                nome_obra=nome_obra,
                valor_brl=valor_brl,
                comissao_brl=comissao_brl,
            )
            send_email(of["editora_terceira_email"],
                       f"Gravan — Comissão creditada: \"{nome_obra}\"",
                       he, te)
        except Exception as e:
            log.warning("Falha ao notificar editora terceira sobre conclusão %s: %s", of.get("id"), e)

    return sb.table("ofertas_licenciamento").select("*").eq("id", of["id"]).single().execute().data


# ─────────────── job: lembretes e expiração ───────────────

def processar_lembretes_e_expiracoes() -> dict:
    """
    Rotina periódica (cron / scheduler interno):
    - envia lembrete 48h e 24h antes do deadline
    - expira ofertas vencidas (cancela PI e estorna)
    Retorne contagens.
    """
    sb = get_supabase()
    now = datetime.now(timezone.utc)
    out = {"reminders_48h": 0, "reminders_24h": 0, "expiradas": 0}

    pendentes = sb.table("ofertas_licenciamento").select("*").in_(
        "status", ["aguardando_editora", "editora_cadastrada", "em_assinatura"]
    ).execute().data or []

    for of in pendentes:
        deadline = datetime.fromisoformat(of["deadline_at"].replace("Z","+00:00"))
        horas = business_hours_remaining(deadline, now)

        # Expirou
        if horas <= 0 and of["status"] != "concluida":
            try:
                _expirar_oferta(of)
                out["expiradas"] += 1
            except Exception as e:
                log.exception("Falha ao expirar oferta %s: %s", of["id"], e)
            continue

        # 24h
        if horas <= 24 and not of.get("reminder_24h_sent_at"):
            try:
                _enviar_lembrete(of, horas_restantes=24)
                sb.table("ofertas_licenciamento").update({
                    "reminder_24h_sent_at": now.isoformat()
                }).eq("id", of["id"]).execute()
                out["reminders_24h"] += 1
            except Exception as e:
                log.exception("Falha lembrete 24h %s: %s", of["id"], e)

        # 48h
        elif horas <= 48 and not of.get("reminder_48h_sent_at"):
            try:
                _enviar_lembrete(of, horas_restantes=48)
                sb.table("ofertas_licenciamento").update({
                    "reminder_48h_sent_at": now.isoformat()
                }).eq("id", of["id"]).execute()
                out["reminders_48h"] += 1
            except Exception as e:
                log.exception("Falha lembrete 48h %s: %s", of["id"], e)

    return out


def _enviar_lembrete(of: dict, horas_restantes: int) -> None:
    sb = get_supabase()
    obra = sb.table("obras").select("nome").eq("id", of["obra_id"]).single().execute().data or {}
    nome_obra = obra.get("nome", "—")
    valor_brl = _moeda(of["valor_cents"])

    # Lembrete para a editora terceira (ação necessária dela)
    h, t = render_oferta_reminder_email(
        nome_editora=of["editora_terceira_nome"],
        nome_obra=nome_obra,
        valor_brl=valor_brl,
        horas_restantes=horas_restantes,
        link=_link_aceitar_oferta(of["registration_token"]),
    )
    send_email(of["editora_terceira_email"],
               f"Gravan — Faltam {horas_restantes}h úteis para responder à oferta",
               h, t)

    # Lembrete informativo para compositor e coautores
    try:
        for c in _get_compositores(of["obra_id"]):
            hc, tc = render_oferta_lembrete_compositor_email(
                nome=c["nome"],
                nome_obra=nome_obra,
                valor_brl=valor_brl,
                horas_restantes=horas_restantes,
            )
            send_email(c["email"],
                       f"Gravan — Oferta de \"{nome_obra}\" expira em ~{horas_restantes}h",
                       hc, tc)
    except Exception as e:
        log.warning("Falha ao enviar lembrete aos compositores da oferta %s: %s", of.get("id"), e)


def _expirar_oferta(of: dict) -> None:
    sb = get_supabase()
    pi_id = of.get("stripe_payment_intent_id")

    # Cancela PaymentIntent (libera hold; se já capturado, faz refund)
    if pi_id:
        try:
            pi = stripe.PaymentIntent.retrieve(pi_id)
            if pi.status in ("requires_capture", "requires_payment_method", "requires_confirmation", "requires_action"):
                stripe.PaymentIntent.cancel(pi_id)
            elif pi.status == "succeeded":
                stripe.Refund.create(payment_intent=pi_id)
        except stripe.StripeError as e:
            log.error("Erro Stripe ao expirar PI %s: %s", pi_id, e)

    sb.table("ofertas_licenciamento").update({
        "status":         "expirada",
        "expirada_em":    datetime.now(timezone.utc).isoformat(),
        "reembolsada_em": datetime.now(timezone.utc).isoformat(),
    }).eq("id", of["id"]).execute()

    obra = sb.table("obras").select("nome").eq("id", of["obra_id"]).single().execute().data or {}
    comprador = sb.table("perfis").select("nome, email").eq("id", of["comprador_id"]).single().execute().data or {}
    if comprador.get("email"):
        h, t = render_oferta_expirada_comprador_email(
            comprador.get("nome") or "Intérprete",
            obra.get("nome", "—"),
            _moeda(of["valor_cents"]),
        )
        send_email(comprador["email"],
                   "Gravan — Oferta expirada e valor estornado", h, t)

    # Avisa também a editora
    h2, t2 = render_oferta_expirada_editora_email(
        of["editora_terceira_nome"], obra.get("nome", "—"),
    )
    send_email(of["editora_terceira_email"],
               "Gravan — Prazo da oferta expirado", h2, t2)

    # Avisa compositor e coautores sobre a expiração
    try:
        nome_obra = obra.get("nome", "—")
        valor_brl = _moeda(of["valor_cents"])
        for c in _get_compositores(of["obra_id"]):
            hc, tc = render_oferta_expirada_compositor_email(
                nome=c["nome"],
                nome_obra=nome_obra,
                valor_brl=valor_brl,
            )
            send_email(c["email"],
                       f"Gravan — Oferta de licenciamento expirada: \"{nome_obra}\"",
                       hc, tc)
    except Exception as e:
        log.warning("Falha ao notificar compositores sobre expiração %s: %s", of.get("id"), e)
