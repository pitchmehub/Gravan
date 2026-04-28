"""
Routes: /api/transacoes
Apenas leitura. Criacao de transacoes agora e via /api/stripe/checkout.
"""
from flask import Blueprint, jsonify, g
from middleware.auth import require_auth
from db.supabase_client import get_supabase

transacoes_bp = Blueprint("transacoes", __name__)


@transacoes_bp.route("/minhas", methods=["GET"])
@require_auth
def minhas_transacoes():
    """Historico de compras do interprete autenticado."""
    sb = get_supabase()
    resp = (
        sb.table("transacoes")
        .select("id, created_at, confirmed_at, status, metodo, valor_cents, obras(nome)")
        .eq("comprador_id", g.user.id)
        .order("created_at", desc=True)
        .limit(100)
        .execute()
    )
    return jsonify(resp.data or []), 200


@transacoes_bp.route("/minhas-vendas", methods=["GET"])
@require_auth
def minhas_vendas():
    """
    Histórico de vendas do compositor / editora autenticado(a).

    Lista cada licenciamento (transação confirmada) em que o usuário recebeu
    crédito — seja como titular, coautor ou editora agregada. Os valores
    refletem exatamente o que foi pago a este perfil em cada venda.

    Cada item:
      - data, transacao_id
      - obra { id, nome }
      - comprador { id, nome }
      - titular { id, nome }
      - valor_total_cents (transação)
      - valor_recebido_cents (o que este perfil recebeu)
      - share_pct
      - sou_titular (bool)
    """
    sb = get_supabase()

    pagamentos = (
        sb.table("pagamentos_compositores")
        .select("id, transacao_id, valor_cents, share_pct, created_at")
        .eq("perfil_id", g.user.id)
        .order("created_at", desc=True)
        .limit(200)
        .execute()
    ).data or []

    if not pagamentos:
        return jsonify({"itens": [], "total_cents": 0, "total_transacoes": 0}), 200

    tx_ids = list({p["transacao_id"] for p in pagamentos if p.get("transacao_id")})

    tx_map = {}
    if tx_ids:
        try:
            tx = (sb.table("transacoes")
                    .select("id, valor_cents, status, created_at, obra_id, comprador_id, "
                            "obras(id, nome, titular_id), "
                            "comprador:perfis!comprador_id(id, nome, nome_completo, nome_artistico)")
                    .in_("id", tx_ids).execute()).data or []
            tx_map = {t["id"]: t for t in tx}
        except Exception:
            try:
                tx = (sb.table("transacoes")
                        .select("id, valor_cents, status, created_at, obra_id, comprador_id")
                        .in_("id", tx_ids).execute()).data or []
                tx_map = {t["id"]: t for t in tx}
            except Exception:
                tx_map = {}

    titular_ids = set()
    for t in tx_map.values():
        obra = t.get("obras") or {}
        if obra.get("titular_id"):
            titular_ids.add(obra["titular_id"])

    titular_map = {}
    if titular_ids:
        try:
            tit = (sb.table("perfis")
                     .select("id, nome, nome_completo, nome_artistico")
                     .in_("id", list(titular_ids)).execute()).data or []
            titular_map = {p["id"]: p for p in tit}
        except Exception:
            pass

    itens = []
    total_cents = 0
    transacoes_unicas = set()
    for p in pagamentos:
        t = tx_map.get(p.get("transacao_id")) or {}
        obra = t.get("obras") or {}
        titular = titular_map.get(obra.get("titular_id")) or {}
        comprador = t.get("comprador") or {}
        recebido = int(p.get("valor_cents") or 0)
        total_cents += recebido
        if p.get("transacao_id"):
            transacoes_unicas.add(p["transacao_id"])
        itens.append({
            "id":                   p["id"],
            "data":                 p.get("created_at") or t.get("created_at"),
            "transacao_id":         p.get("transacao_id"),
            "valor_total_cents":    t.get("valor_cents"),
            "valor_recebido_cents": recebido,
            "share_pct":            p.get("share_pct"),
            "sou_titular":          obra.get("titular_id") == g.user.id,
            "obra": {
                "id":   obra.get("id"),
                "nome": obra.get("nome"),
            },
            "titular": {
                "id":   titular.get("id"),
                "nome": titular.get("nome_artistico") or titular.get("nome_completo") or titular.get("nome"),
            },
            "comprador": {
                "id":   comprador.get("id"),
                "nome": comprador.get("nome_artistico") or comprador.get("nome_completo") or comprador.get("nome"),
            },
        })

    return jsonify({
        "itens": itens,
        "total_cents": total_cents,
        "total_transacoes": len(transacoes_unicas),
    }), 200
