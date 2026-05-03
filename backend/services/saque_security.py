"""
Lógica de segurança do fluxo de saque com OTP + janela de 24h.

Fluxo:
  1) iniciar_saque(perfil_id, valor_cents, ip, ua)
       → cria registro 'pendente_otp', envia OTP por e-mail
  2) confirmar_otp(saque_id, perfil_id, codigo)
       → valida OTP, agenda liberação para now()+24h, envia e-mail "Não fui eu?"
  3) cancelar_pelo_dono(saque_id, perfil_id, motivo)  -- via app, autenticado
     cancelar_por_token(token, motivo)                -- via link de e-mail
       → marca como 'cancelado', NÃO debitou wallet ainda nessa altura
  4) liberar_pendentes()                               -- chamado por cron
       → busca status='aguardando_liberacao' com liberar_em<=now()
       → debita wallet, executa Transfer Stripe, marca 'pago'

Limites:
  - Mínimo R$ 10,00 (1000 cents)
  - Máximo R$ 5.000,00 por dia (configurável via SAQUE_LIMITE_DIARIO_CENTS)
  - Máximo 3 saques pendente_otp/aguardando_liberacao por usuário ao mesmo tempo
  - OTP: 6 dígitos, 10 min de validade, máximo 5 tentativas
"""
import os
import hmac
import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import stripe

from db.supabase_client import get_supabase
from services.email_service import (
    send_email,
    render_otp_email,
    render_saque_agendado_email,
    render_saque_pago_email,
    render_saque_cancelado_email,
)
from services.saque_calendar import (
    janela_atual,
    saque_permitido_hoje,
    primeiro_dia_do_mes_iso,
    ultimo_dia_util_do_mes,
)

log = logging.getLogger("gravan.saque")

# ────────── Configurações ──────────
OTP_VALIDADE_MIN          = 10
OTP_MAX_TENTATIVAS        = 5
JANELA_LIBERACAO_HORAS    = int(os.environ.get("SAQUE_JANELA_HORAS", "12"))
# Sem limites por valor/quantidade — o único requisito é ter saldo disponível.
VALOR_MIN_CENTS           = 1  # qualquer valor positivo é aceito


# ────────── Helpers de hash com pepper ──────────
def _pepper() -> bytes:
    """Pepper derivado do FLASK_SECRET_KEY para impedir reverse-lookup do OTP."""
    secret = os.environ.get("FLASK_SECRET_KEY") or os.environ.get("SESSION_SECRET") or "dev-pepper"
    return secret.encode()


def _hash_otp(codigo: str) -> str:
    return hmac.new(_pepper(), codigo.encode(), hashlib.sha256).hexdigest()


def _hash_token(token: str) -> str:
    return hmac.new(_pepper(), token.encode(), hashlib.sha256).hexdigest()


def _hash_ip(ip: Optional[str]) -> Optional[str]:
    if not ip:
        return None
    return hmac.new(_pepper(), ip.encode(), hashlib.sha256).hexdigest()[:32]


def _fmt_brl(cents: int) -> str:
    return f"R$ {cents/100:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ────────── Validações ──────────
def _validar_perfil_pode_sacar(sb, perfil_id: str) -> dict:
    """Devolve o perfil ou levanta ValueError com mensagem amigável."""
    try:
        p = sb.table("perfis").select(
            "id, email, nome, nome_artistico, "
            "stripe_account_id, stripe_charges_enabled, stripe_payouts_enabled"
        ).eq("id", perfil_id).maybe_single().execute()
        perfil = (p.data if p else None) or {}
    except Exception as _exc:
        _m = str(_exc).lower()
        if "column" in _m or "does not exist" in _m or "42703" in _m:
            raise RuntimeError(
                "Execute migration_stripe_connect.sql no Supabase SQL Editor "
                "antes de usar saques."
            )
        raise
    if not perfil:
        raise ValueError("Perfil não encontrado.")
    if not perfil.get("email"):
        raise ValueError("Cadastre um e-mail no seu perfil antes de sacar.")
    if not perfil.get("stripe_account_id"):
        raise ValueError("Conecte sua conta Stripe antes de sacar (Receber pagamentos).")
    if not perfil.get("stripe_charges_enabled"):
        raise ValueError("Sua conta Stripe ainda está em verificação. Conclua o cadastro.")
    return perfil


def _saldo_atual(sb, perfil_id: str) -> int:
    w = sb.table("wallets").select("saldo_cents").eq("perfil_id", perfil_id).maybe_single().execute()
    return ((w.data if w else None) or {}).get("saldo_cents") or 0


def _reservado_em_pendentes(sb, perfil_id: str) -> int:
    """Soma valores de saques ainda não-finais — eles 'reservam' saldo."""
    r = sb.table("saques").select("valor_cents, status").eq("perfil_id", perfil_id).execute()
    return sum(
        int(s["valor_cents"] or 0) for s in (r.data or [])
        if s.get("status") in ("pendente_otp", "aguardando_liberacao", "processando")
    )


def _sacado_ultimas_24h(sb, perfil_id: str) -> int:
    """Soma o que já foi confirmado/pago nas últimas 24h."""
    cutoff = (_now() - timedelta(hours=24)).isoformat()
    r = (sb.table("saques")
         .select("valor_cents, status, confirmado_em, created_at")
         .eq("perfil_id", perfil_id)
         .gte("created_at", cutoff)
         .execute())
    return sum(
        int(s["valor_cents"] or 0) for s in (r.data or [])
        if s.get("status") in ("aguardando_liberacao", "processando", "pago")
    )


def _ja_sacou_este_mes(sb, perfil_id: str) -> bool:
    """True se o usuário já tem um saque ativo (não cancelado) iniciado este mês."""
    cutoff = primeiro_dia_do_mes_iso()
    r = (sb.table("saques")
         .select("id, status")
         .eq("perfil_id", perfil_id)
         .gte("created_at", cutoff)
         .execute())
    ATIVOS = ("pendente_otp", "aguardando_liberacao", "processando", "pago")
    return any(s.get("status") in ATIVOS for s in (r.data or []))


# ────────── (1) Iniciar saque ──────────
def iniciar_saque(
    perfil_id: str,
    valor_cents: int,
    ip: str,
    user_agent: str,
    *,
    auto: bool = False,
) -> dict:
    """
    Inicia um saque. `auto=True` significa que veio do cron de fim de mês
    (pula validação de janela e validação manual de once-per-month porque
    o cron já filtra os elegíveis).
    """
    sb = get_supabase()

    if not isinstance(valor_cents, int) or valor_cents < VALOR_MIN_CENTS:
        raise ValueError("Informe um valor válido para sacar.")

    perfil = _validar_perfil_pode_sacar(sb, perfil_id)

    saldo       = _saldo_atual(sb, perfil_id)
    reservado   = _reservado_em_pendentes(sb, perfil_id)
    disponivel  = saldo - reservado
    if valor_cents > disponivel:
        raise ValueError(
            f"Saldo disponível: {_fmt_brl(disponivel)} "
            f"({_fmt_brl(reservado)} já reservado em saques em andamento)."
        )

    # Sem limites de quantidade, valor diário ou janela mensal —
    # o usuário pode fazer quantos saques quiser desde que tenha saldo.

    # Gera OTP de 6 dígitos
    codigo = f"{secrets.randbelow(1_000_000):06d}"
    otp_hash = _hash_otp(codigo)
    expires  = (_now() + timedelta(minutes=OTP_VALIDADE_MIN)).isoformat()

    try:
        ins = sb.table("saques").insert({
            "perfil_id":         perfil_id,
            "valor_cents":       valor_cents,
            "status":            "pendente_otp",
            "metodo":            "stripe",
            "stripe_account_id": perfil.get("stripe_account_id"),
            "otp_hash":          otp_hash,
            "otp_expires_at":    expires,
            "otp_attempts":      0,
            "ip_hash":           _hash_ip(ip),
            "user_agent":        (user_agent or "")[:500],
        }).execute()
    except Exception as _exc:
        _m = str(_exc).lower()
        if "column" in _m or "does not exist" in _m or "42703" in _m:
            raise RuntimeError(
                "Execute migration_saque_otp.sql no Supabase SQL Editor."
            )
        raise
    if not ins.data:
        raise RuntimeError("Não foi possível registrar a solicitação de saque.")
    saque_id = ins.data[0]["id"]

    html, text = render_otp_email(
        nome=perfil.get("nome_artistico") or perfil.get("nome") or "",
        codigo=codigo, valor_brl=_fmt_brl(valor_cents), ip=ip or "-",
    )
    send_email(perfil["email"], "Gravan — Código de confirmação de saque", html, text)

    return {
        "saque_id": saque_id,
        "expira_em_segundos": OTP_VALIDADE_MIN * 60,
        "email_destino_mascarado": _mask_email(perfil["email"]),
    }


def _mask_email(email: str) -> str:
    if not email or "@" not in email:
        return email or ""
    user, dom = email.split("@", 1)
    if len(user) <= 2:
        return f"{user[0]}***@{dom}"
    return f"{user[:2]}***{user[-1]}@{dom}"


# ────────── (2) Confirmar OTP ──────────
def confirmar_otp(saque_id: str, perfil_id: str, codigo: str, frontend_origin: str) -> dict:
    sb = get_supabase()

    s = sb.table("saques").select("*").eq("id", saque_id).eq("perfil_id", perfil_id) \
        .maybe_single().execute()
    saque = (s.data if s else None)
    if not saque:
        raise ValueError("Solicitação de saque não encontrada.")
    if saque.get("status") != "pendente_otp":
        raise ValueError("Esta solicitação não está aguardando confirmação.")

    # Validade
    expires_at = saque.get("otp_expires_at")
    if not expires_at or datetime.fromisoformat(expires_at.replace("Z", "+00:00")) < _now():
        sb.table("saques").update({"status": "expirado"}).eq("id", saque_id).execute()
        raise ValueError("Código expirado. Inicie um novo saque.")

    # Tentativas
    if int(saque.get("otp_attempts") or 0) >= OTP_MAX_TENTATIVAS:
        sb.table("saques").update({"status": "expirado"}).eq("id", saque_id).execute()
        raise ValueError("Muitas tentativas. Esta solicitação foi cancelada por segurança.")

    # Compara em tempo constante
    codigo = (codigo or "").strip()
    if not codigo.isdigit() or len(codigo) != 6 \
       or not hmac.compare_digest(_hash_otp(codigo), saque["otp_hash"] or ""):
        sb.table("saques").update({
            "otp_attempts": int(saque.get("otp_attempts") or 0) + 1
        }).eq("id", saque_id).execute()
        raise ValueError("Código inválido.")

    # Sucesso → agenda liberação para 24h
    cancel_token  = secrets.token_urlsafe(32)
    libera_em_dt  = _now() + timedelta(hours=JANELA_LIBERACAO_HORAS)

    sb.table("saques").update({
        "status":            "aguardando_liberacao",
        "confirmado_em":     _now().isoformat(),
        "liberar_em":        libera_em_dt.isoformat(),
        "cancel_token_hash": _hash_token(cancel_token),
        "otp_hash":          None,         # já não precisa mais
        "otp_expires_at":    None,
    }).eq("id", saque_id).execute()

    # E-mail de confirmação + link "não fui eu"
    perfil = sb.table("perfis").select("email, nome, nome_artistico") \
        .eq("id", perfil_id).maybe_single().execute().data or {}
    cancel_url = f"{frontend_origin.rstrip('/')}/saques/cancelar?token={cancel_token}"
    libera_em_str = libera_em_dt.astimezone(timezone(timedelta(hours=-3))) \
                                .strftime("%d/%m/%Y às %H:%M (BRT)")
    html, text = render_saque_agendado_email(
        nome=perfil.get("nome_artistico") or perfil.get("nome") or "",
        valor_brl=_fmt_brl(saque["valor_cents"]),
        libera_em=libera_em_str, cancel_url=cancel_url,
    )
    send_email(perfil.get("email", ""), "Gravan — Saque agendado (24h)", html, text)

    return {
        "saque_id":   saque_id,
        "status":     "aguardando_liberacao",
        "liberar_em": libera_em_dt.isoformat(),
    }


# ────────── (3) Cancelamento ──────────
def _cancelar(sb, saque: dict, motivo: str) -> dict:
    sb.table("saques").update({
        "status":           "cancelado",
        "cancelado_em":     _now().isoformat(),
        "cancelado_motivo": (motivo or "")[:300],
        "cancel_token_hash": None,
    }).eq("id", saque["id"]).execute()

    perfil = sb.table("perfis").select("email, nome, nome_artistico") \
        .eq("id", saque["perfil_id"]).maybe_single().execute().data or {}
    html, text = render_saque_cancelado_email(
        nome=perfil.get("nome_artistico") or perfil.get("nome") or "",
        valor_brl=_fmt_brl(saque["valor_cents"]),
        motivo=motivo or "Cancelamento solicitado pelo titular",
    )
    send_email(perfil.get("email", ""), "Gravan — Saque cancelado", html, text)
    return {"ok": True, "saque_id": saque["id"], "status": "cancelado"}


def cancelar_pelo_dono(saque_id: str, perfil_id: str, motivo: str = "") -> dict:
    sb = get_supabase()
    s = sb.table("saques").select("*").eq("id", saque_id).eq("perfil_id", perfil_id) \
        .maybe_single().execute()
    saque = s.data if s else None
    if not saque:
        raise ValueError("Saque não encontrado.")
    if saque["status"] not in ("pendente_otp", "aguardando_liberacao"):
        raise ValueError("Este saque já foi processado e não pode mais ser cancelado.")
    return _cancelar(sb, saque, motivo or "Cancelado pelo usuário no app")


def cancelar_por_token(token: str, motivo: str = "") -> dict:
    if not token or len(token) < 16:
        raise ValueError("Link inválido.")
    sb = get_supabase()
    h = _hash_token(token)
    r = sb.table("saques").select("*").eq("cancel_token_hash", h).maybe_single().execute()
    saque = r.data if r else None
    if not saque:
        raise ValueError("Link inválido ou já utilizado.")
    if saque["status"] != "aguardando_liberacao":
        raise ValueError("Este saque não pode mais ser cancelado.")
    return _cancelar(sb, saque, motivo or "Cancelado via link 'não fui eu'")


# ────────── (4) Liberação por cron ──────────
def _ensure_stripe():
    if not stripe.api_key:
        stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")


def liberar_pendentes(limite: int = 25) -> dict:
    """
    Chamado por cron a cada poucos minutos.
    Pega saques com janela vencida, debita wallet, executa Transfer Stripe.
    """
    _ensure_stripe()
    sb = get_supabase()

    # Marca lote como 'processando' usando RPC com FOR UPDATE SKIP LOCKED
    try:
        rpc = sb.rpc("saques_a_liberar", {"p_limit": limite}).execute()
        a_processar = rpc.data or []
    except Exception as e:
        log.error("Falha ao chamar saques_a_liberar: %s — fallback select.", e)
        agora = _now().isoformat()
        sel = (sb.table("saques").select("*")
               .eq("status", "aguardando_liberacao")
               .lte("liberar_em", agora).limit(limite).execute())
        a_processar = sel.data or []
        for s in a_processar:
            sb.table("saques").update({"status": "processando"}).eq("id", s["id"]).execute()

    # Expira OTPs antigos de uma vez
    try:
        sb.rpc("saques_expirar_otps", {}).execute()
    except Exception:
        pass

    pagos, falhas = 0, 0
    for saque in a_processar:
        try:
            _processar_um_saque(sb, saque)
            pagos += 1
        except Exception as e:
            falhas += 1
            log.error("Falha ao processar saque %s: %s", saque.get("id"), e)
            sb.table("saques").update({
                "status":           "rejeitado",
                "cancelado_motivo": f"Erro Stripe: {str(e)[:280]}",
            }).eq("id", saque["id"]).execute()

    return {"processados": len(a_processar), "pagos": pagos, "falhas": falhas}


def _buscar_charge_id_da_transacao(sb, transacao_id: str) -> Optional[str]:
    """
    Busca o ID da Charge Stripe (ch_xxx) vinculada a uma transação.
    Necessário para `source_transaction` em Transfers com Connect Brasil.
    """
    if not transacao_id:
        return None
    t = sb.table("transacoes").select("stripe_payment_intent") \
        .eq("id", transacao_id).maybe_single().execute()
    pi_id = ((t.data if t else None) or {}).get("stripe_payment_intent")
    if not pi_id:
        return None
    try:
        pi = stripe.PaymentIntent.retrieve(pi_id, expand=["latest_charge"])
        ch = pi.get("latest_charge")
        if isinstance(ch, dict):
            return ch.get("id")
        return ch  # já é string
    except Exception as e:
        log.warning("Falha ao buscar charge do PI %s: %s", pi_id, e)
        return None


def _debitar_wallet_atomico(sb, perfil_id: str, valor_cents: int, saque_id: str) -> None:
    """
    Debita a wallet via RPC com SELECT FOR UPDATE (exclusão mútua real por linha).
    Lança RuntimeError se saldo insuficiente ou carteira não encontrada.
    Esta é a ÚNICA forma de debitar saldo — nunca fazer UPDATE direto.
    """
    try:
        res = sb.rpc("debitar_wallet", {
            "p_perfil_id":   perfil_id,
            "p_valor_cents": valor_cents,
            "p_saque_id":    saque_id,
        }).execute()
        resultado = res.data if res else None
        # PostgREST pode retornar lista ou dict
        if isinstance(resultado, list):
            resultado = resultado[0] if resultado else None
        if not resultado or not resultado.get("ok"):
            erro = (resultado or {}).get("erro", "Saldo insuficiente.")
            raise RuntimeError(f"Débito recusado pelo banco: {erro}")
    except RuntimeError:
        raise
    except Exception as e:
        # RPC não existe ainda → fallback seguro com checagem manual + UPDATE condicional
        log.warning("RPC debitar_wallet indisponível (%s) — usando fallback com checagem.", e)
        saldo = _saldo_atual(sb, perfil_id)
        if saldo < valor_cents:
            raise RuntimeError(
                f"Saldo insuficiente (fallback): {_fmt_brl(saldo)} disponíveis, "
                f"{_fmt_brl(valor_cents)} solicitados."
            )
        # UPDATE condicional: só debita se saldo ainda for suficiente.
        # Não é 100% atômico sem FOR UPDATE, mas é muito melhor que o upsert cego.
        novo = saldo - valor_cents
        sb.table("wallets").update({"saldo_cents": novo}).eq(
            "perfil_id", perfil_id
        ).gte("saldo_cents", valor_cents).execute()
        # Verifica se o UPDATE de fato alterou algo (saldo pode ter caído entre a leitura e o UPDATE)
        saldo_pos = _saldo_atual(sb, perfil_id)
        if saldo_pos != novo:
            raise RuntimeError(
                "Débito falhou por condição de corrida — saldo alterado concorrentemente. "
                "Saque não processado."
            )


def _reconstitui_wallet(sb, perfil_id: str, valor_cents: int, motivo: str) -> None:
    """Reverte um débito já feito. Chamado quando os Transfers Stripe falham."""
    try:
        sb.rpc("creditar_wallet", {
            "p_perfil_id":   perfil_id,
            "p_valor_cents": valor_cents,
        }).execute()
        log.info("Wallet reconstituída para %s (+%d cents): %s", perfil_id, valor_cents, motivo)
    except Exception as e:
        log.error(
            "CRÍTICO: falha ao reconstituir wallet de %s (+%d cents) após erro Stripe. "
            "Requer reconciliação manual. Motivo: %s. Erro reconstituição: %s",
            perfil_id, valor_cents, motivo, e,
        )


def _processar_um_saque(sb, saque: dict) -> None:
    """
    Libera um saque criando UMA Stripe Transfer por charge de origem,
    cada uma com `source_transaction=ch_xxx` (obrigatório no Brasil).

    ORDEM OBRIGATÓRIA DE SEGURANÇA (nunca alterar):
      0. Valida saldo e pagamentos rastreáveis.
      1. DEBITA WALLET ATOMICAMENTE (RPC com FOR UPDATE) — antes de qualquer chamada Stripe.
         Se falhar aqui, nada externo foi modificado.
      2. Cria Stripe Transfers.
         Se qualquer Transfer falhar → reverte Transfers criados + RECONSTITUI wallet.
      3. Atualiza pagamentos_compositores (marcação de uso).
      4. Finaliza saque como 'pago'.

    Isso garante que:
      - Nunca se gasta mais do que o saldo real (constraint + RPC com lock).
      - Dois processos paralelos para o mesmo perfil não causam double-spend
        (o segundo bloqueia no FOR UPDATE e vê saldo já decrementado).
      - Em caso de falha Stripe, a wallet é restaurada antes de propagar o erro.
    """
    perfil_id   = saque["perfil_id"]
    valor_cents = int(saque["valor_cents"])
    saque_id    = saque["id"]
    acc_id      = saque.get("stripe_account_id")
    if not acc_id:
        raise RuntimeError("Conta Stripe não vinculada no saque.")

    # ── 0a) Valida saldo atual ──
    saldo = _saldo_atual(sb, perfil_id)
    if saldo < valor_cents:
        raise RuntimeError(f"Saldo insuficiente no momento da liberação ({_fmt_brl(saldo)}).")

    # ── 0b) Valida pagamentos rastreáveis suficientes ──
    pend_q = (sb.table("pagamentos_compositores")
              .select("id, valor_cents, transacao_id, stripe_charge_id, "
                      "coautoria_id, share_pct, perfil_id")
              .eq("perfil_id", perfil_id)
              .eq("status", "pendente")
              .is_("saque_id", "null")
              .order("created_at", desc=False)
              .execute())
    pendentes = pend_q.data or []
    soma_disp = sum(int(p["valor_cents"] or 0) for p in pendentes)
    if soma_disp < valor_cents:
        raise RuntimeError(
            f"Pagamentos rastreáveis insuficientes ({_fmt_brl(soma_disp)} de "
            f"{_fmt_brl(valor_cents)} pedidos). Há saldo legado sem origem "
            f"vinculada — só é possível sacar valores até esse limite."
        )

    # ── 0c) Garante charge_id em cada pagamento ──
    for p in pendentes:
        if not p.get("stripe_charge_id"):
            ch_id = _buscar_charge_id_da_transacao(sb, p["transacao_id"])
            if ch_id:
                sb.table("pagamentos_compositores").update({
                    "stripe_charge_id": ch_id,
                }).eq("id", p["id"]).execute()
                p["stripe_charge_id"] = ch_id

    # ══════════════════════════════════════════════════════════════
    # PASSO 1 — DÉBITO ATÔMICO ANTES DE QUALQUER CHAMADA STRIPE
    # Qualquer falha aqui é segura: nenhum Transfer foi criado ainda.
    # ══════════════════════════════════════════════════════════════
    _debitar_wallet_atomico(sb, perfil_id, valor_cents, saque_id)
    log.info("Wallet debitada atomicamente: perfil=%s, valor=%d, saque=%s",
             perfil_id, valor_cents, saque_id)

    # ══════════════════════════════════════════════════════════════
    # PASSO 2 — Cria Stripe Transfers (após débito confirmado)
    # Em caso de falha: reverte Transfers + RECONSTITUI wallet.
    # ══════════════════════════════════════════════════════════════
    restante = valor_cents
    transfers_criados: list = []
    stripe_falhou = False
    stripe_erro_msg = ""

    for p in pendentes:
        if restante <= 0:
            break
        if not p.get("stripe_charge_id"):
            stripe_falhou = True
            stripe_erro_msg = (
                f"Pagamento {p['id']} (transação {p['transacao_id']}) sem "
                f"charge Stripe vinculada."
            )
            break
        original = int(p["valor_cents"])
        consumir = min(original, restante)
        try:
            tr = stripe.Transfer.create(
                amount=consumir,
                currency="brl",
                destination=acc_id,
                source_transaction=p["stripe_charge_id"],
                metadata={
                    "saque_id":     str(saque_id),
                    "pagamento_id": str(p["id"]),
                    "perfil_id":    str(perfil_id),
                },
                idempotency_key=f"saque_{saque_id}_pag_{p['id']}",
            )
        except stripe.StripeError as e:
            log.error("Stripe Transfer falhou no pag %s: %s", p["id"], e)
            stripe_falhou = True
            stripe_erro_msg = (
                f"Stripe rejeitou Transfer do pagamento {p['id']}: "
                f"{getattr(e, 'user_message', None) or str(e)}"
            )
            break
        transfers_criados.append((tr.id, p["id"], consumir, original, p))
        restante -= consumir

    if stripe_falhou:
        # Reverte os Transfers parcialmente criados
        _reverter_transfers(transfers_criados)
        # Reconstitui o saldo que foi debitado — débito nunca deve ficar sem Transfer
        _reconstitui_wallet(sb, perfil_id, valor_cents,
                            f"rollback após falha Stripe: {stripe_erro_msg}")
        raise RuntimeError(stripe_erro_msg)

    # ── Passo 3) Atualiza pagamentos (consumo total ou parcial) ──
    agora_iso = _now().isoformat()
    for tr_id, pag_id, consumido, original, orig_row in transfers_criados:
        if consumido >= original:
            sb.table("pagamentos_compositores").update({
                "saque_id":            saque_id,
                "status":              "pago",
                "stripe_transfer_id":  tr_id,
                "liberado_em":         agora_iso,
            }).eq("id", pag_id).execute()
        else:
            sb.table("pagamentos_compositores").update({
                "valor_cents": original - consumido,
            }).eq("id", pag_id).execute()
            sb.table("pagamentos_compositores").insert({
                "perfil_id":          orig_row["perfil_id"],
                "transacao_id":       orig_row["transacao_id"],
                "coautoria_id":       orig_row.get("coautoria_id"),
                "share_pct":          orig_row.get("share_pct"),
                "valor_cents":        consumido,
                "status":             "pago",
                "saque_id":           saque_id,
                "stripe_transfer_id": tr_id,
                "stripe_charge_id":   orig_row.get("stripe_charge_id"),
                "liberado_em":        agora_iso,
            }).execute()

    # ── Passo 4) Finaliza saque ──
    primary_tr = transfers_criados[0][0] if transfers_criados else None
    sb.table("saques").update({
        "status":             "pago",
        "stripe_transfer_id": primary_tr,
        "processed_at":       agora_iso,
    }).eq("id", saque_id).execute()

    # E-mail de confirmação
    perfil = sb.table("perfis").select("email, nome, nome_artistico") \
        .eq("id", perfil_id).maybe_single().execute().data or {}
    try:
        html, text = render_saque_pago_email(
            nome=perfil.get("nome_artistico") or perfil.get("nome") or "",
            valor_brl=_fmt_brl(valor_cents),
            transfer_id=primary_tr or "(múltiplos)",
        )
        send_email(perfil.get("email", ""), "Gravan — Saque enviado ✓", html, text)
    except Exception as e:
        log.warning("E-mail de saque pago falhou: %s", e)


def _reverter_transfers(criados: list) -> None:
    """Best-effort: reverte Transfers já criados quando há erro no meio."""
    for item in criados:
        tr_id = item[0]
        try:
            stripe.Transfer.create_reversal(tr_id, metadata={"motivo": "rollback_saque"})
        except Exception as e:
            log.error("Falha ao reverter transfer %s: %s", tr_id, e)


# ────────── (5) Auto-criação no último dia útil ──────────
def auto_criar_mensal(limite: int = 100, valor_min_cents: int = VALOR_MIN_CENTS) -> dict:
    """
    Cron rodado às 00:01 do último dia útil de cada mês.
    Para cada perfil com:
      - saldo_disponivel >= valor_min_cents
      - sem saque ativo neste mês
      - stripe_charges_enabled = true
    cria um saque automático com status 'aguardando_liberacao' (pula OTP).
    O cron normal (`liberar_pendentes`) pega depois e executa o transfer.
    """
    info = janela_atual()

    # Só roda no último dia útil (defesa adicional — cheap check antes do DB)
    if not info.get("eh_ultimo_dia_util"):
        return {"executado": False, "motivo": f"Hoje ({info['hoje']}) não é o último dia útil. Próximo: {info['fim']}."}

    sb = get_supabase()

    # Busca quem tem saldo
    wallets = sb.table("wallets").select("perfil_id, saldo_cents") \
        .gte("saldo_cents", valor_min_cents).limit(limite).execute()
    candidatos = wallets.data or []

    criados, pulados, falhas = 0, 0, 0
    detalhes = []
    libera_em_dt = _now() + timedelta(hours=JANELA_LIBERACAO_HORAS)

    for w in candidatos:
        perfil_id = w["perfil_id"]
        saldo = int(w["saldo_cents"] or 0)
        try:
            # Pula quem já tem saque ativo este mês
            if _ja_sacou_este_mes(sb, perfil_id):
                pulados += 1
                detalhes.append({"perfil_id": perfil_id, "status": "pulado_ja_sacou"})
                continue

            # Valida perfil + Stripe Connect
            try:
                perfil = _validar_perfil_pode_sacar(sb, perfil_id)
            except ValueError as e:
                pulados += 1
                detalhes.append({"perfil_id": perfil_id, "status": f"pulado_{e}"[:80]})
                continue

            # Saca o saldo TOTAL disponível (descontado o que já está reservado)
            reservado = _reservado_em_pendentes(sb, perfil_id)
            valor_cents = saldo - reservado
            if valor_cents < valor_min_cents:
                pulados += 1
                detalhes.append({"perfil_id": perfil_id, "status": "pulado_saldo_baixo"})
                continue

            # Cria direto em 'aguardando_liberacao' (sem OTP — é automático)
            ins = sb.table("saques").insert({
                "perfil_id":         perfil_id,
                "valor_cents":       valor_cents,
                "status":            "aguardando_liberacao",
                "metodo":            "stripe",
                "stripe_account_id": perfil.get("stripe_account_id"),
                "confirmado_em":     _now().isoformat(),
                "liberar_em":        libera_em_dt.isoformat(),
            }).execute()
            saque_id = ins.data[0]["id"] if ins.data else None
            criados += 1
            detalhes.append({"perfil_id": perfil_id, "status": "criado", "saque_id": saque_id, "valor_cents": valor_cents})

            # Email avisando
            try:
                libera_em_str = libera_em_dt.astimezone(timezone(timedelta(hours=-3))) \
                                            .strftime("%d/%m/%Y às %H:%M (BRT)")
                html, text = render_saque_agendado_email(
                    nome=perfil.get("nome_artistico") or perfil.get("nome") or "",
                    valor_brl=_fmt_brl(valor_cents),
                    libera_em=libera_em_str,
                    cancel_url="",  # auto-saque não tem link "não fui eu"
                )
                send_email(perfil["email"], "Gravan — Saque automático agendado", html, text)
            except Exception as e:
                log.warning("Email de auto-saque falhou para %s: %s", perfil_id, e)

        except Exception as e:
            falhas += 1
            log.error("auto_criar_mensal falhou para perfil %s: %s", perfil_id, e)
            detalhes.append({"perfil_id": perfil_id, "status": f"erro_{str(e)[:60]}"})

    return {
        "executado": True,
        "data": info["fim"],
        "candidatos": len(candidatos),
        "criados": criados,
        "pulados": pulados,
        "falhas": falhas,
        "detalhes": detalhes,
    }
