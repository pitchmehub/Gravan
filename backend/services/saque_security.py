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

log = logging.getLogger("pitchme.saque")

# ────────── Configurações ──────────
OTP_VALIDADE_MIN          = 10
OTP_MAX_TENTATIVAS        = 5
JANELA_LIBERACAO_HORAS    = int(os.environ.get("SAQUE_JANELA_HORAS", "24"))
LIMITE_DIARIO_CENTS       = int(os.environ.get("SAQUE_LIMITE_DIARIO_CENTS", str(500_000)))  # R$5.000
LIMITE_PENDENTES_USUARIO  = int(os.environ.get("SAQUE_MAX_PENDENTES", "3"))
VALOR_MIN_CENTS           = 1000


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


# ────────── (1) Iniciar saque ──────────
def iniciar_saque(perfil_id: str, valor_cents: int, ip: str, user_agent: str) -> dict:
    sb = get_supabase()

    if not isinstance(valor_cents, int) or valor_cents < VALOR_MIN_CENTS:
        raise ValueError(f"Valor mínimo: R$ {VALOR_MIN_CENTS/100:.2f}")

    perfil = _validar_perfil_pode_sacar(sb, perfil_id)

    saldo       = _saldo_atual(sb, perfil_id)
    reservado   = _reservado_em_pendentes(sb, perfil_id)
    disponivel  = saldo - reservado
    if valor_cents > disponivel:
        raise ValueError(
            f"Saldo disponível: {_fmt_brl(disponivel)} "
            f"({_fmt_brl(reservado)} já reservado em saques em andamento)."
        )

    # Limite diário
    sacado24 = _sacado_ultimas_24h(sb, perfil_id)
    if sacado24 + valor_cents > LIMITE_DIARIO_CENTS:
        restante = max(0, LIMITE_DIARIO_CENTS - sacado24)
        raise ValueError(
            f"Limite diário de saque ({_fmt_brl(LIMITE_DIARIO_CENTS)}) atingido. "
            f"Disponível hoje: {_fmt_brl(restante)}."
        )

    # Limite de pendentes simultâneos
    n_pendentes = sum(
        1 for s in (sb.table("saques").select("status").eq("perfil_id", perfil_id).execute().data or [])
        if s.get("status") in ("pendente_otp", "aguardando_liberacao")
    )
    if n_pendentes >= LIMITE_PENDENTES_USUARIO:
        raise ValueError(
            f"Você já tem {n_pendentes} saques aguardando confirmação ou liberação. "
            f"Aguarde concluí-los."
        )

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
    send_email(perfil["email"], "Pitch.me — Código de confirmação de saque", html, text)

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
    send_email(perfil.get("email", ""), "Pitch.me — Saque agendado (24h)", html, text)

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
    send_email(perfil.get("email", ""), "Pitch.me — Saque cancelado", html, text)
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


def _processar_um_saque(sb, saque: dict) -> None:
    perfil_id   = saque["perfil_id"]
    valor_cents = int(saque["valor_cents"])
    acc_id      = saque.get("stripe_account_id")
    if not acc_id:
        raise RuntimeError("Conta Stripe não vinculada no saque.")

    # Re-checa saldo (pode ter mudado nas 24h)
    saldo = _saldo_atual(sb, perfil_id)
    if saldo < valor_cents:
        raise RuntimeError(f"Saldo insuficiente no momento da liberação ({_fmt_brl(saldo)}).")

    # Cria Transfer (idempotente pelo saque_id)
    tr = stripe.Transfer.create(
        amount=valor_cents,
        currency="brl",
        destination=acc_id,
        metadata={"saque_id": str(saque["id"]), "perfil_id": str(perfil_id)},
        idempotency_key=f"saque_{saque['id']}",
    )

    # Debita wallet
    novo_saldo = saldo - valor_cents
    sb.table("wallets").upsert({
        "perfil_id": perfil_id, "saldo_cents": novo_saldo,
    }).execute()

    sb.table("saques").update({
        "status":             "pago",
        "stripe_transfer_id": tr.id,
    }).eq("id", saque["id"]).execute()

    # E-mail
    perfil = sb.table("perfis").select("email, nome, nome_artistico") \
        .eq("id", perfil_id).maybe_single().execute().data or {}
    html, text = render_saque_pago_email(
        nome=perfil.get("nome_artistico") or perfil.get("nome") or "",
        valor_brl=_fmt_brl(valor_cents), transfer_id=tr.id,
    )
    send_email(perfil.get("email", ""), "Pitch.me — Saque enviado ✓", html, text)
