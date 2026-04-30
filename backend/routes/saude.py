"""
Routes: /api/admin/saude — Painel de saúde do sistema (apenas administradores)

Fornece status consolidado de:
  - Backend (uptime, versão/commit, ambiente, workers)
  - Banco de dados (Supabase ping com latência)
  - Variáveis de ambiente críticas (set / missing — sem expor valores)
  - Integrações externas (Stripe, Sentry, Redis, Push)
  - Últimas violações de CSP capturadas
  - Migrações pendentes
"""
import os
import time
import platform
import subprocess
from collections import deque
from datetime import datetime, timezone

from flask import Blueprint, jsonify, current_app, request, g, abort
from middleware.auth import require_auth
from db.supabase_client import get_supabase
from services.migrations_status import summary as migrations_summary

saude_bp = Blueprint("saude", __name__)


@saude_bp.before_request
def _enforce_admin():
    """Mesma camada de proteção do admin_bp: exige JWT + role administrador."""
    from middleware.auth import _get_cached_user, _cache_user

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        abort(401, description="Token de autenticação ausente.")

    jwt = auth_header.split(" ", 1)[1]
    if len(jwt) < 20 or len(jwt) > 2000:
        abort(401, description="Token inválido.")

    user = _get_cached_user(jwt)
    if user is None:
        try:
            sb = get_supabase()
            user_resp = sb.auth.get_user(jwt)
            if not user_resp or not user_resp.user:
                abort(401, description="Token inválido ou expirado.")
            user = user_resp.user
            _cache_user(jwt, user)
        except Exception:
            abort(401, description="Falha ao validar o token.")

    g.user = user
    g.jwt = jwt

    sb = get_supabase()
    r = sb.table("perfis").select("role").eq("id", g.user.id).single().execute()
    if not r.data or r.data.get("role") != "administrador":
        abort(403, description="Acesso restrito a administradores.")

_BOOT_TIME = time.time()

CSP_VIOLATIONS: deque = deque(maxlen=50)


def record_csp_violation(payload: dict) -> None:
    """Chamado pelo handler /api/csp-report do app.py."""
    try:
        CSP_VIOLATIONS.appendleft({
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "payload": payload,
        })
    except Exception:
        pass


def _git_commit() -> dict:
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL
        ).decode().strip()
    except Exception:
        commit = ""
    try:
        msg = subprocess.check_output(
            ["git", "log", "-1", "--pretty=%s"], stderr=subprocess.DEVNULL
        ).decode().strip()
    except Exception:
        msg = ""
    return {"commit": commit, "commit_short": commit[:12], "commit_msg": msg}


def _check_env_vars() -> dict:
    """Lista o status de variáveis críticas SEM expor seus valores."""
    grupos = {
        "Banco de dados": [
            "SUPABASE_URL",
            ("SUPABASE_SERVICE_KEY", "SUPABASE_SERVICE_ROLE_KEY"),
            "SUPABASE_ANON_KEY",
        ],
        "Sessão / Auth": [
            "FLASK_SECRET_KEY",
            "PII_ENCRYPTION_KEY",
        ],
        "Pagamentos (Stripe)": [
            "STRIPE_SECRET_KEY",
            "STRIPE_WEBHOOK_SECRET",
            "STRIPE_PUBLISHABLE_KEY",
        ],
        "Push notifications": [
            "VAPID_PUBLIC_KEY",
            "VAPID_PRIVATE_KEY",
            "VAPID_SUBJECT",
        ],
        "Observabilidade": [
            "SENTRY_DSN_BACKEND",
            "REDIS_URL",
        ],
        "Cron / Saques": [
            "SAQUE_CRON_SECRET",
        ],
    }
    resultado = {}
    for grupo, chaves in grupos.items():
        items = []
        for k in chaves:
            if isinstance(k, tuple):
                # qualquer um do par satisfaz
                presente = any(bool(os.getenv(x)) for x in k)
                items.append({
                    "name": " ou ".join(k),
                    "set": presente,
                })
            else:
                items.append({
                    "name": k,
                    "set": bool(os.getenv(k)),
                })
        resultado[grupo] = items
    return resultado


def _check_db() -> dict:
    """Faz um ping leve no Supabase (count em uma tabela pequena)."""
    inicio = time.time()
    try:
        sb = get_supabase()
        sb.table("perfis").select("id", count="exact").limit(1).execute()
        latencia_ms = round((time.time() - inicio) * 1000, 1)
        return {
            "status": "ok",
            "latencia_ms": latencia_ms,
            "mensagem": "Conexão estabelecida.",
        }
    except KeyError as e:
        return {
            "status": "erro",
            "latencia_ms": None,
            "mensagem": f"Variável de ambiente ausente: {e}",
        }
    except Exception as e:
        return {
            "status": "erro",
            "latencia_ms": round((time.time() - inicio) * 1000, 1),
            "mensagem": f"{type(e).__name__}: {str(e)[:200]}",
        }


def _check_stripe() -> dict:
    """Verifica se a API do Stripe responde com a chave configurada."""
    secret = os.getenv("STRIPE_SECRET_KEY", "")
    if not secret:
        return {"status": "nao_configurado", "mensagem": "STRIPE_SECRET_KEY não definida."}
    inicio = time.time()
    try:
        import stripe
        stripe.api_key = secret
        stripe.Account.retrieve()
        return {
            "status": "ok",
            "latencia_ms": round((time.time() - inicio) * 1000, 1),
            "modo": "live" if secret.startswith("sk_live_") else "test",
        }
    except Exception as e:
        return {
            "status": "erro",
            "mensagem": f"{type(e).__name__}: {str(e)[:200]}",
        }


def _check_redis() -> dict:
    url = os.getenv("REDIS_URL", "")
    if not url or url.startswith("memory://"):
        return {"status": "memoria", "mensagem": "Rate limiter usando memória local (não persistente)."}
    try:
        import redis
        r = redis.from_url(url, socket_connect_timeout=2, socket_timeout=2)
        inicio = time.time()
        r.ping()
        return {"status": "ok", "latencia_ms": round((time.time() - inicio) * 1000, 1)}
    except Exception as e:
        return {"status": "erro", "mensagem": f"{type(e).__name__}: {str(e)[:200]}"}


@saude_bp.route("/saude", methods=["GET"])
@require_auth
def saude_geral():
    """Status consolidado da plataforma para o painel administrativo."""
    uptime_s = time.time() - _BOOT_TIME

    db = _check_db()
    stripe_st = _check_stripe()
    redis_st = _check_redis()
    env_status = _check_env_vars()

    try:
        migr = migrations_summary()
    except Exception as e:
        migr = {"erro": str(e)[:200]}

    # Verifica saúde geral
    componentes_ok = (
        db["status"] == "ok"
        and stripe_st["status"] in ("ok", "nao_configurado")
        and redis_st["status"] in ("ok", "memoria")
    )

    return jsonify({
        "status_geral": "ok" if componentes_ok else "degradado",
        "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "backend": {
            "uptime_segundos": round(uptime_s, 0),
            "uptime_humano": _fmt_uptime(uptime_s),
            "ambiente": os.getenv("FLASK_ENV", "development"),
            "python": platform.python_version(),
            "platform": platform.platform(),
            "host": platform.node(),
            **_git_commit(),
        },
        "banco_dados": db,
        "stripe": stripe_st,
        "redis": redis_st,
        "variaveis_ambiente": env_status,
        "migracoes": migr,
        "csp_violations": {
            "total_capturadas": len(CSP_VIOLATIONS),
            "ultimas": list(CSP_VIOLATIONS)[:10],
        },
    }), 200


def _fmt_uptime(s: float) -> str:
    s = int(s)
    d, s = divmod(s, 86400)
    h, s = divmod(s, 3600)
    m, s = divmod(s, 60)
    partes = []
    if d: partes.append(f"{d}d")
    if h: partes.append(f"{h}h")
    if m and not d: partes.append(f"{m}m")
    if not partes: partes.append(f"{s}s")
    return " ".join(partes)
