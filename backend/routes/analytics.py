"""Routes: /api/analytics — Métricas de engajamento, economia e financeiro.

Aberto a TODOS os compositores autenticados:
  - Compositor PRO: vê valores reais de economia (5% sobre cada venda).
  - Compositor STARTER: vê os MESMOS valores como "potencial" — quanto teria
    economizado se fosse PRO. Funciona como atrativo para upgrade.
"""
from datetime import datetime, timezone
from flask import Blueprint, jsonify, g, abort, request
from middleware.auth import require_auth
from middleware.plano import require_pro
from db.supabase_client import get_supabase
from services.migration_check import migration_applied
from services.subscription import PRO_PRICE_CENTS
from utils.crypto import hash_ip
from app import limiter

analytics_bp = Blueprint("analytics", __name__)


# Diferença entre fee STARTER (20%) e fee PRO (15%) = 5%.
ECONOMIA_PRO_FRACTION = 0.05


def _is_pro(perfil: dict) -> bool:
    return (
        perfil.get("plano") == "PRO"
        and perfil.get("status_assinatura") in ("ativa", "cancelada", "past_due")
    )


def _start_of_month_utc() -> str:
    now = datetime.now(timezone.utc)
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()


@analytics_bp.route("/resumo", methods=["GET"])
@require_auth
def resumo():
    """Métricas agregadas de engajamento + economia + financeiro do compositor.

    Aberto a STARTER e PRO. Para STARTER, os valores de economia representam
    o quanto teria economizado se fosse PRO (atrativo para upgrade).
    """
    sb = get_supabase()

    perfil = (
        sb.table("perfis")
        .select("id, plano, status_assinatura, assinatura_inicio")
        .eq("id", g.user.id)
        .single()
        .execute()
        .data
        or {}
    )
    is_pro_user = _is_pro(perfil)

    # ── Engajamento (plays / curtidas) ────────────────────────────
    obras_resp = (
        sb.table("obras")
        .select("id, nome, preco_cents, cover_url")
        .eq("titular_id", g.user.id)
        .execute()
    )
    obras = obras_resp.data or []
    obra_ids = [o["id"] for o in obras]

    plays_map: dict[str, dict] = {}
    if obra_ids and migration_applied():
        try:
            stats = (
                sb.table("obra_analytics")
                .select("obra_id, plays_count, favorites_count, last_played_at")
                .in_("obra_id", obra_ids)
                .execute()
            )
            plays_map = {s["obra_id"]: s for s in (stats.data or [])}
        except Exception:
            plays_map = {}

    # ── Financeiro (transações confirmadas em que o titular é o usuário) ──
    inicio_mes = _start_of_month_utc()
    receita_total_cents = 0
    receita_mes_cents = 0
    obras_receita: dict[str, int] = {o["id"]: 0 for o in obras}

    if obra_ids:
        try:
            txs = (
                sb.table("transacoes")
                .select("id, obra_id, valor_cents, liquido_cents, status, confirmed_at")
                .in_("obra_id", obra_ids)
                .eq("status", "confirmada")
                .execute()
                .data
                or []
            )
        except Exception:
            txs = []

        for tx in txs:
            valor = int(tx.get("valor_cents") or 0)
            liquido = int(tx.get("liquido_cents") or 0) or int(round(valor * 0.85 if is_pro_user else valor * 0.80))
            receita_total_cents += valor
            obras_receita[tx["obra_id"]] = obras_receita.get(tx["obra_id"], 0) + valor

            confirmed_at = tx.get("confirmed_at")
            if confirmed_at and confirmed_at >= inicio_mes:
                receita_mes_cents += valor

    # ── Economia PRO (real para PRO, potencial para STARTER) ──────
    economia_total_cents = int(round(receita_total_cents * ECONOMIA_PRO_FRACTION))
    economia_mes_cents = int(round(receita_mes_cents * ECONOMIA_PRO_FRACTION))

    # ROI da assinatura (mês corrente)
    roi_pct: float | None = None
    if PRO_PRICE_CENTS > 0:
        roi_pct = round(
            ((economia_mes_cents - PRO_PRICE_CENTS) / PRO_PRICE_CENTS) * 100, 1
        )

    # ── Monta lista de obras com tudo ─────────────────────────────
    lista = []
    total_p = total_f = 0
    for o in obras:
        s = plays_map.get(o["id"], {})
        p = int(s.get("plays_count") or 0)
        f = int(s.get("favorites_count") or 0)
        total_p += p
        total_f += f
        lista.append({
            "obra_id": o["id"],
            "nome": o["nome"],
            "cover_url": o.get("cover_url"),
            "preco_cents": o.get("preco_cents") or 0,
            "plays": p,
            "favoritos": f,
            "last_played_at": s.get("last_played_at"),
            "receita_cents": obras_receita.get(o["id"], 0),
        })

    # Ranking de engajamento (plays + 3*favoritos)
    ranking_engajamento = sorted(
        lista, key=lambda x: x["plays"] + x["favoritos"] * 3, reverse=True
    )
    # Ranking por receita
    ranking_receita = sorted(
        lista, key=lambda x: x["receita_cents"], reverse=True
    )

    # Receita líquida (após comissão da plataforma)
    fee_rate = 0.15 if is_pro_user else 0.20
    receita_liquida_total_cents = int(round(receita_total_cents * (1 - fee_rate)))
    receita_liquida_mes_cents = int(round(receita_mes_cents * (1 - fee_rate)))

    return jsonify({
        "is_pro": is_pro_user,
        "plano": perfil.get("plano") or "STARTER",
        "assinatura_pro_cents": PRO_PRICE_CENTS,
        "assinatura_inicio": perfil.get("assinatura_inicio"),

        # Engajamento
        "total_plays": total_p,
        "total_favoritos": total_f,
        "obras": ranking_engajamento,

        # Economia PRO (real ou potencial conforme is_pro)
        "economia_mes_cents": economia_mes_cents,
        "economia_total_cents": economia_total_cents,
        "roi_mes_pct": roi_pct,

        # Financeiro
        "receita_mes_cents": receita_mes_cents,
        "receita_total_cents": receita_total_cents,
        "receita_liquida_mes_cents": receita_liquida_mes_cents,
        "receita_liquida_total_cents": receita_liquida_total_cents,
        "ranking_receita": ranking_receita,
    }), 200


@analytics_bp.route("/obra/<obra_id>", methods=["GET"])
@require_auth
@require_pro
def detalhe_obra(obra_id):
    """Métricas detalhadas de uma obra específica (só o titular, exclusivo PRO)."""
    sb = get_supabase()
    o = sb.table("obras").select("titular_id, nome").eq("id", obra_id).single().execute()
    if not o.data:
        abort(404, description="Obra não encontrada.")
    if o.data["titular_id"] != g.user.id:
        abort(403, description="Apenas o titular pode ver as métricas desta obra.")

    stats = sb.table("obra_analytics").select("*").eq("obra_id", obra_id).limit(1).execute()
    s = (stats.data or [{}])[0]
    return jsonify({
        "obra_id":          obra_id,
        "nome":             o.data["nome"],
        "plays":            int(s.get("plays_count") or 0),
        "favoritos":        int(s.get("favorites_count") or 0),
        "last_played_at":   s.get("last_played_at"),
    }), 200


# ─────────────────────────────────────────────────────────────────
# Endpoint público de registro de play (não exige PRO nem auth)
# ─────────────────────────────────────────────────────────────────
@analytics_bp.route("/play/<obra_id>", methods=["POST"])
@limiter.limit("120 per hour")
def registrar_play(obra_id):
    """Registra um play para alimentar analytics. Público, rate-limited por IP."""
    if not migration_applied():
        return jsonify({"ok": True, "skipped": True}), 200
    sb = get_supabase()
    o = sb.table("obras").select("id").eq("id", obra_id).limit(1).execute()
    if not o.data:
        abort(404, description="Obra não encontrada.")

    # Identifica usuário se houver JWT
    perfil_id = None
    try:
        from middleware.auth import extract_user_if_present
        u = extract_user_if_present()
        perfil_id = u.id if u else None
    except Exception:
        perfil_id = None

    try:
        sb.table("play_events").insert({
            "obra_id":   obra_id,
            "perfil_id": perfil_id,
            "ip_hash":   hash_ip(request.remote_addr or ""),
        }).execute()
    except Exception:
        pass
    return jsonify({"ok": True}), 200
