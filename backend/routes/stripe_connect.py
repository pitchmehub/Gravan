"""
Routes: /api/connect — Stripe Connect (Express Accounts)

Onboarding dos compositores para receberem payouts via Stripe Connect.
Cada autor/coautor precisa completar o onboarding antes de receber transfers.
"""
import os
import time
import logging
import stripe
from flask import Blueprint, request, jsonify, g, abort

from middleware.auth import require_auth
from db.supabase_client import get_supabase
from app import limiter

logger = logging.getLogger("pitchme.connect")

connect_bp = Blueprint("connect", __name__)
stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")
FRONTEND_URL   = os.environ.get("FRONTEND_URL", "http://localhost:5173")


def _ensure_key():
    if not stripe.api_key:
        stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")
    if not stripe.api_key:
        abort(500, description="Stripe não configurado: STRIPE_SECRET_KEY ausente.")


_MIGRATION_HINT = (
    "Banco de dados desatualizado: rode a migration "
    "`backend/db/migration_stripe_connect.sql` no Supabase antes de usar "
    "Stripe Connect."
)


def _get_perfil(uid: str) -> dict:
    """Lê o perfil. Se as colunas stripe_* ainda não existem, usa defaults.
    Cria perfil mínimo se não existir (caso usuário só esteja em auth.users).
    """
    sb = get_supabase()
    cols_full = ("id, email, nome, nome_completo, stripe_account_id, "
                 "stripe_charges_enabled, stripe_payouts_enabled, "
                 "stripe_onboarding_completo")
    cols_basic = "id, email, nome, nome_completo"

    def _is_transient(exc: Exception) -> bool:
        m = str(exc).lower()
        # Erros transitórios típicos (Windows: WinError 10035 socket non-blocking,
        # 10054/10060 reset/timeout; httpx ReadTimeout; conexão fechada).
        return any(k in m for k in (
            "10035", "10053", "10054", "10060", "10061",
            "winerror", "non-blocking", "sem bloqueio",
            "timed out", "timeout", "connection reset",
            "remotedisconnected", "connectionerror", "readerror",
        ))

    def _query(cols):
        # select + limit(1) é estável; .single()/.maybe_single() lança 204
        # Retry simples para erros de socket transitórios (comum no Windows).
        last_exc = None
        for tentativa in range(3):
            try:
                r = sb.table("perfis").select(cols).eq("id", uid).limit(1).execute()
                rows = r.data or []
                return rows[0] if rows else None
            except Exception as exc:
                last_exc = exc
                if not _is_transient(exc):
                    raise
                logger.warning("Tentativa %d falhou (transitório): %s", tentativa + 1, exc)
                time.sleep(0.3 * (tentativa + 1))
        raise last_exc

    migration_pendente = False
    try:
        data = _query(cols_full)
    except Exception as e:
        msg = str(e).lower()
        if "column" in msg and "stripe_" in msg:
            logger.error("Colunas stripe_* não existem. %s", _MIGRATION_HINT)
            migration_pendente = True
            try:
                data = _query(cols_basic)
            except Exception as e2:
                logger.error("Falha fallback perfil: %s", e2)
                abort(500, description=_MIGRATION_HINT)
        else:
            logger.error("Erro ao buscar perfil: %s", e)
            abort(500, description=f"Erro ao buscar perfil: {e}")

    if not data:
        # Perfil não existe na tabela ainda: cria mínimo a partir do JWT
        email = getattr(g.user, "email", None)
        try:
            ins = sb.table("perfis").insert({
                "id":    uid,
                "email": email,
                "nome":  (email or "").split("@")[0] or "Usuário",
            }).execute()
            data = (ins.data or [{}])[0]
        except Exception as e:
            logger.error("Falha ao criar perfil mínimo: %s", e)
            abort(404, description="Perfil não encontrado e não foi possível criar automaticamente.")

    data.setdefault("stripe_account_id", None)
    data.setdefault("stripe_charges_enabled", False)
    data.setdefault("stripe_payouts_enabled", False)
    data.setdefault("stripe_onboarding_completo", False)
    if migration_pendente:
        data["_migration_pendente"] = True
    return data


def _safe_update_perfil(perfil_id: str, fields: dict) -> None:
    """Update tolerante: se colunas stripe_* não existem, ignora."""
    try:
        get_supabase().table("perfis").update(fields).eq("id", perfil_id).execute()
    except Exception as e:
        logger.warning("Falha ao atualizar perfil (%s): %s", list(fields), e)


# ─── 1. Onboarding ─────────────────────────────────────────────────────
@connect_bp.route("/onboarding", methods=["POST"])
@require_auth
@limiter.limit("10 per hour")
def criar_onboarding():
    """
    Cria (ou recupera) a conta Express e devolve link de onboarding hosted
    pela Stripe. O frontend redireciona o usuário para essa URL.
    """
    _ensure_key()
    perfil = _get_perfil(g.user.id)

    account_id = perfil.get("stripe_account_id")
    if not account_id:
        try:
            acc = stripe.Account.create(
                type="express",
                country="BR",
                email=perfil.get("email") or g.user.email,
                capabilities={
                    "transfers":     {"requested": True},
                    "card_payments": {"requested": True},
                },
                business_type="individual",
                metadata={"perfil_id": str(perfil["id"])},
            )
            account_id = acc.id
            if perfil.get("_migration_pendente"):
                abort(500, description=_MIGRATION_HINT)
            _safe_update_perfil(perfil["id"], {"stripe_account_id": account_id})
            logger.info("Conta Connect criada: %s para perfil %s", account_id, perfil["id"])
        except stripe.error.StripeError as e:
            logger.error("Falha ao criar conta Connect: %s", e)
            abort(500, description=f"Erro Stripe: {e.user_message or str(e)}")

    try:
        link = stripe.AccountLink.create(
            account=account_id,
            refresh_url=f"{FRONTEND_URL}/connect/refresh",
            return_url=f"{FRONTEND_URL}/connect/sucesso",
            type="account_onboarding",
        )
    except stripe.error.StripeError as e:
        abort(500, description=f"Erro ao gerar link: {e.user_message or str(e)}")

    return jsonify({"url": link.url, "account_id": account_id}), 200


# ─── 2. Status atual da conta ──────────────────────────────────────────
@connect_bp.route("/status", methods=["GET"])
@require_auth
def status_conta():
    """Devolve o estado atual da conta Connect do usuário (sincroniza com Stripe)."""
    _ensure_key()
    perfil = _get_perfil(g.user.id)
    account_id = perfil.get("stripe_account_id")

    if not account_id:
        return jsonify({
            "conectado": False,
            "charges_enabled": False,
            "payouts_enabled": False,
            "onboarding_completo": False,
            "requirements": None,
        }), 200

    try:
        acc = stripe.Account.retrieve(account_id)
    except stripe.error.StripeError as e:
        logger.warning("Falha ao consultar Stripe Account %s: %s", account_id, e)
        return jsonify({
            "conectado": True,
            "account_id": account_id,
            "erro": "Não foi possível consultar a Stripe agora.",
        }), 200

    charges_enabled = bool(acc.get("charges_enabled"))
    payouts_enabled = bool(acc.get("payouts_enabled"))
    details_submitted = bool(acc.get("details_submitted"))
    requirements = (acc.get("requirements") or {}).get("currently_due") or []

    # Sincroniza no banco (se as colunas existirem)
    _safe_update_perfil(perfil["id"], {
        "stripe_charges_enabled":      charges_enabled,
        "stripe_payouts_enabled":      payouts_enabled,
        "stripe_onboarding_completo":  details_submitted and charges_enabled,
        "stripe_account_atualizado_em": "now()",
    })

    return jsonify({
        "conectado": True,
        "account_id": account_id,
        "charges_enabled": charges_enabled,
        "payouts_enabled": payouts_enabled,
        "details_submitted": details_submitted,
        "onboarding_completo": details_submitted and charges_enabled,
        "requirements_pendentes": requirements,
    }), 200


# ─── 3. Login no dashboard Express ─────────────────────────────────────
@connect_bp.route("/dashboard-link", methods=["POST"])
@require_auth
@limiter.limit("20 per hour")
def gerar_dashboard_link():
    """Cria um link de uso único pro dashboard Express (Stripe-hosted)."""
    _ensure_key()
    perfil = _get_perfil(g.user.id)
    account_id = perfil.get("stripe_account_id")
    if not account_id:
        abort(404, description="Você ainda não conectou sua conta Stripe.")
    try:
        link = stripe.Account.create_login_link(account_id)
    except stripe.error.StripeError as e:
        abort(500, description=f"Erro Stripe: {e.user_message or str(e)}")
    return jsonify({"url": link.url}), 200


# ─── 4. Listar repasses do usuário logado ──────────────────────────────
@connect_bp.route("/repasses", methods=["GET"])
@require_auth
def listar_repasses():
    """Lista os repasses do usuário (transfers Stripe) com totalizador."""
    sb = get_supabase()
    r = sb.table("repasses").select(
        "id, valor_cents, share_pct, status, stripe_transfer_id, "
        "created_at, enviado_at, liberado_at, erro_msg, "
        "transacoes(id, valor_cents, obras(id, nome))"
    ).eq("perfil_id", g.user.id).order("created_at", desc=True).limit(200).execute()

    items = r.data or []
    totais = {"enviado": 0, "retido": 0, "pendente": 0, "falhou": 0}
    for it in items:
        s = it["status"]
        if s in totais:
            totais[s] += it["valor_cents"]

    return jsonify({"items": items, "totais_cents": totais}), 200
