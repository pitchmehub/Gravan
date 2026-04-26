"""
Rotas REST do fluxo de saque com OTP + janela de 24h.

Endpoints:
  POST  /api/saques/iniciar               (auth) → cria pendente_otp + envia e-mail
  POST  /api/saques/<id>/confirmar        (auth) → valida OTP, agenda liberação 24h
  POST  /api/saques/<id>/reenviar-otp     (auth) → gera novo OTP (rate-limit forte)
  POST  /api/saques/<id>/cancelar         (auth) → dono cancela enquanto pendente
  POST  /api/saques/cancelar-por-token    (público) → link "Não fui eu" do e-mail
  POST  /api/saques/processar-pendentes   (cron) → libera saques com janela vencida
"""
import os
import logging
from flask import Blueprint, request, jsonify, g, abort

from middleware.auth import require_auth
from app import limiter
from utils.audit import log_event
from services.saque_security import (
    iniciar_saque,
    confirmar_otp,
    cancelar_pelo_dono,
    cancelar_por_token,
    liberar_pendentes,
    auto_criar_mensal,
    _ja_sacou_este_mes,
)
from services.saque_calendar import janela_atual
from db.supabase_client import get_supabase

log = logging.getLogger("gravan.saques.routes")
saques_bp = Blueprint("saques", __name__, url_prefix="/api/saques")


def _ip() -> str:
    return request.headers.get("X-Forwarded-For", request.remote_addr or "").split(",")[0].strip()


def _frontend_origin() -> str:
    origin = request.headers.get("Origin") or request.headers.get("Referer") or ""
    if origin.startswith("http"):
        # Mantém só esquema+host, descarta path
        from urllib.parse import urlparse
        p = urlparse(origin)
        return f"{p.scheme}://{p.netloc}"
    return os.environ.get("FRONTEND_URL", "https://gravan")


# ──────────────────────────────────────────────────────────
# 1. Iniciar saque (envia OTP por e-mail)
# ──────────────────────────────────────────────────────────
@saques_bp.route("/iniciar", methods=["POST"])
@require_auth
def iniciar():
    data = request.get_json(silent=True) or {}
    try:
        valor_cents = int(data.get("valor_cents") or 0)
    except (TypeError, ValueError):
        abort(422, description="Valor inválido.")

    try:
        r = iniciar_saque(
            perfil_id=g.user.id,
            valor_cents=valor_cents,
            ip=_ip(),
            user_agent=request.headers.get("User-Agent", ""),
        )
    except ValueError as e:
        abort(422, description=str(e))
    except Exception as e:
        log.exception("iniciar_saque falhou: %s", e)
        abort(500, description="Erro interno ao iniciar saque.")

    log_event("saque.iniciado", entity_type="saque", entity_id=r["saque_id"],
              metadata={"valor_cents": valor_cents})
    return jsonify(r), 201


# ──────────────────────────────────────────────────────────
# 2. Confirmar OTP
# ──────────────────────────────────────────────────────────
@saques_bp.route("/<saque_id>/confirmar", methods=["POST"])
@require_auth
def confirmar(saque_id):
    data = request.get_json(silent=True) or {}
    codigo = (data.get("codigo") or "").strip()
    if not codigo:
        abort(422, description="Código obrigatório.")

    try:
        r = confirmar_otp(
            saque_id=saque_id,
            perfil_id=g.user.id,
            codigo=codigo,
            frontend_origin=_frontend_origin(),
        )
    except ValueError as e:
        abort(422, description=str(e))
    except Exception as e:
        log.exception("confirmar_otp falhou: %s", e)
        abort(500, description="Erro interno ao confirmar saque.")

    log_event("saque.confirmado", entity_type="saque", entity_id=saque_id,
              metadata={"liberar_em": r["liberar_em"]})

    try:
        from services.notificacoes import notify
        from db.supabase_client import get_supabase
        sb = get_supabase()
        s = sb.table("saques").select("valor_cents").eq("id", saque_id).maybe_single().execute()
        valor = (s.data or {}).get("valor_cents", 0) if s else 0
        valor_brl = f"R$ {valor/100:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        notify(
            g.user.id,
            tipo="saque_confirmado",
            titulo="Saque confirmado",
            mensagem=f"Seu saque de {valor_brl} foi confirmado e será processado.",
            link="/saques",
            payload={"saque_id": saque_id, "liberar_em": r.get("liberar_em")},
        )
    except Exception:
        pass

    return jsonify(r), 200


# ──────────────────────────────────────────────────────────
# 3. Reenviar OTP (apenas se ainda estiver pendente_otp)
# ──────────────────────────────────────────────────────────
@saques_bp.route("/<saque_id>/reenviar-otp", methods=["POST"])
@require_auth
def reenviar(saque_id):
    """Cancela o saque atual e cria um novo com mesmo valor — gera novo OTP."""
    from db.supabase_client import get_supabase
    sb = get_supabase()
    s = sb.table("saques").select("*").eq("id", saque_id).eq("perfil_id", g.user.id) \
        .maybe_single().execute()
    saque = s.data if s else None
    if not saque:
        abort(404, description="Saque não encontrado.")
    if saque.get("status") != "pendente_otp":
        abort(422, description="Só é possível reenviar para saques aguardando confirmação.")

    # Cancela o atual (sem e-mail de cancelamento — é só substituição)
    sb.table("saques").update({
        "status": "expirado", "otp_hash": None, "otp_expires_at": None,
    }).eq("id", saque_id).execute()

    # Cria novo
    try:
        novo = iniciar_saque(
            perfil_id=g.user.id,
            valor_cents=int(saque["valor_cents"]),
            ip=_ip(),
            user_agent=request.headers.get("User-Agent", ""),
        )
    except ValueError as e:
        abort(422, description=str(e))
    return jsonify(novo), 201


# ──────────────────────────────────────────────────────────
# 4. Dono cancela manualmente pelo app
# ──────────────────────────────────────────────────────────
@saques_bp.route("/<saque_id>/cancelar", methods=["POST"])
@require_auth
def cancelar_app(saque_id):
    data = request.get_json(silent=True) or {}
    motivo = (data.get("motivo") or "")[:300]
    try:
        r = cancelar_pelo_dono(saque_id, g.user.id, motivo)
    except ValueError as e:
        abort(422, description=str(e))
    log_event("saque.cancelado", entity_type="saque", entity_id=saque_id,
              metadata={"motivo": motivo, "via": "app"})

    try:
        from services.notificacoes import notify
        notify(
            g.user.id,
            tipo="saque_cancelado",
            titulo="Saque cancelado",
            mensagem="Seu saque foi cancelado conforme solicitado.",
            link="/saques",
            payload={"saque_id": saque_id, "motivo": motivo},
        )
    except Exception:
        pass

    return jsonify(r), 200


# ──────────────────────────────────────────────────────────
# 5. Cancelamento via link público "Não fui eu"
# ──────────────────────────────────────────────────────────
@saques_bp.route("/cancelar-por-token", methods=["POST"])
def cancelar_token():
    data = request.get_json(silent=True) or {}
    token  = (data.get("token") or "").strip()
    motivo = (data.get("motivo") or "Não fui eu (cancelado via link no e-mail)")[:300]
    try:
        r = cancelar_por_token(token, motivo)
    except ValueError as e:
        abort(422, description=str(e))
    log_event("saque.cancelado", entity_type="saque", entity_id=r["saque_id"],
              metadata={"motivo": motivo, "via": "token_email"},
              user_id=None)
    return jsonify(r), 200


# ──────────────────────────────────────────────────────────
# 6. Processador de pendentes (cron) — protegido por header secreto
# ──────────────────────────────────────────────────────────
@saques_bp.route("/processar-pendentes", methods=["POST"])
def processar_pendentes():
    """
    Endpoint chamado por cron externo (Render Cron Job, cron-job.org,
    Supabase Edge Function, GitHub Actions...) a cada 5-10 minutos.

    Header obrigatório:
      X-Cron-Secret: <valor de SAQUE_CRON_SECRET no .env>
    """
    secret_esperado = os.environ.get("SAQUE_CRON_SECRET")
    if not secret_esperado:
        abort(503, description="Cron não configurado (SAQUE_CRON_SECRET ausente).")
    if request.headers.get("X-Cron-Secret") != secret_esperado:
        abort(403, description="Acesso negado.")

    try:
        limite = int(request.args.get("limit", "25"))
    except ValueError:
        limite = 25

    r = liberar_pendentes(limite=limite)
    log.info("Cron processar-pendentes: %s", r)
    return jsonify(r), 200


# ──────────────────────────────────────────────────────────
# 7. Janela mensal de saque (informativo pro dashboard)
# ──────────────────────────────────────────────────────────
@saques_bp.route("/janela", methods=["GET"])
@require_auth
def janela():
    """Saques estão sempre disponíveis — sem janela mensal nem limite de quantidade."""
    info = janela_atual()
    info["aberta"] = True
    info["ja_sacou_este_mes"] = False
    info["pode_sacar_agora"] = True
    return jsonify(info), 200


# ──────────────────────────────────────────────────────────
# 8. Auto-criação mensal (cron — último dia útil 00:01)
# ──────────────────────────────────────────────────────────
@saques_bp.route("/auto-criar-mensal", methods=["POST"])
def auto_criar_mensal_cron():
    """
    Endpoint chamado por cron externo no último dia útil de cada mês.
    Cria saques automáticos para perfis com saldo que não sacaram manualmente.

    Header obrigatório:
      X-Cron-Secret: <valor de SAQUE_CRON_SECRET no .env>
    """
    secret_esperado = os.environ.get("SAQUE_CRON_SECRET")
    if not secret_esperado:
        abort(503, description="Cron não configurado (SAQUE_CRON_SECRET ausente).")
    if request.headers.get("X-Cron-Secret") != secret_esperado:
        abort(403, description="Acesso negado.")

    try:
        limite = int(request.args.get("limit", "100"))
    except ValueError:
        limite = 100

    r = auto_criar_mensal(limite=limite)
    log.info("Cron auto-criar-mensal: %s", r)
    return jsonify(r), 200
