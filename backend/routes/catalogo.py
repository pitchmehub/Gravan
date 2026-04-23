"""
Routes: /api/catalogo  /api/comentarios  /api/ofertas
"""
from flask import Blueprint, request, jsonify, g, abort
from middleware.auth import require_auth, require_role
from db.supabase_client import get_supabase
from utils.sanitizer import sanitize_text

catalogo_bp = Blueprint("catalogo", __name__)

# ──────────────────────────────────────────────
# ESTATÍSTICAS PÚBLICAS (para Landing)
# ──────────────────────────────────────────────

@catalogo_bp.route("/stats/public", methods=["GET"])
def stats_publicas():
    """Retorna estatísticas agregadas da plataforma para exibir na Landing.
    Público — não requer autenticação."""
    import logging
    log = logging.getLogger(__name__)
    sb = get_supabase()

    try:
        obras_resp = sb.table("catalogo_publico").select("id", count="exact").execute()
        total_obras = obras_resp.count if obras_resp.count is not None else len(obras_resp.data or [])
    except Exception as e:
        log.warning("stats_publicas: erro contando obras: %s", e)
        total_obras = 0

    try:
        comp_resp = (
            sb.table("perfis")
            .select("id", count="exact")
            .eq("role", "compositor")
            .execute()
        )
        total_compositores = comp_resp.count if comp_resp.count is not None else len(comp_resp.data or [])
    except Exception as e:
        log.warning("stats_publicas: erro contando compositores: %s", e)
        total_compositores = 0

    try:
        trans_resp = (
            sb.table("transacoes")
            .select("valor_cents")
            .eq("status", "confirmada")
            .execute()
        )
        total_pago_cents = sum(int(t.get("valor_cents") or 0) for t in (trans_resp.data or []))
        total_pago = total_pago_cents / 100.0
    except Exception as e:
        log.warning("stats_publicas: erro somando transações: %s", e)
        total_pago = 0.0

    return jsonify({
        "obras": total_obras,
        "compositores": total_compositores,
        "total_pago": total_pago,
    }), 200


# ──────────────────────────────────────────────
# CATÁLOGO PÚBLICO
# ──────────────────────────────────────────────

@catalogo_bp.route("/", methods=["GET"])
def listar_catalogo():
    genero   = request.args.get("genero")
    busca    = request.args.get("q", "").strip()
    page     = max(1, int(request.args.get("page", 1)))
    per_page = min(50, int(request.args.get("per_page", 20)))
    offset   = (page - 1) * per_page

    sb = get_supabase()
    query = (
        sb.table("catalogo_publico")
        .select("*")
        .order("created_at", desc=True)
        .range(offset, offset + per_page - 1)
    )
    if genero:
        query = query.eq("genero", genero)
    if busca:
        query = query.ilike("nome", f"%{busca}%")

    resp = query.execute()
    return jsonify(resp.data or []), 200


@catalogo_bp.route("/<obra_id>", methods=["GET"])
def detalhe_obra(obra_id):
    sb = get_supabase()
    try:
        resp = (
            sb.table("catalogo_publico")
            .select("*")
            .eq("id", obra_id)
            .maybe_single()
            .execute()
        )
    except Exception:
        abort(404, description="Obra não encontrada.")
    if not resp or not resp.data:
        abort(404, description="Obra não encontrada.")
    return jsonify(resp.data), 200


# ──────────────────────────────────────────────
# COMENTÁRIOS
# ──────────────────────────────────────────────

@catalogo_bp.route("/<obra_id>/comentarios", methods=["GET"])
def listar_comentarios(obra_id):
    sb = get_supabase()
    resp = (
        sb.table("comentarios")
        .select("*, perfis(nome, avatar_url, nivel)")
        .eq("obra_id", obra_id)
        .order("created_at", desc=True)
        .execute()
    )
    return jsonify(resp.data or []), 200


@catalogo_bp.route("/<obra_id>/comentarios", methods=["POST"])
@require_auth
def criar_comentario(obra_id):
    data = request.get_json(force=True, silent=True) or {}
    conteudo_raw = data.get("conteudo", "")

    try:
        conteudo = sanitize_text(conteudo_raw, max_length=1000)
    except ValueError as e:
        abort(422, description=str(e))

    if not conteudo:
        abort(422, description="Comentário não pode estar vazio.")

    sb = get_supabase()
    resp = (
        sb.table("comentarios")
        .insert({"obra_id": obra_id, "perfil_id": g.user.id, "conteudo": conteudo})
        .execute()
    )
    return jsonify(resp.data[0]), 201


@catalogo_bp.route("/comentarios/<comentario_id>", methods=["DELETE"])
@require_auth
def deletar_comentario(comentario_id):
    sb = get_supabase()
    # RLS garante que só o autor pode deletar
    sb.table("comentarios").delete().eq("id", comentario_id).eq("perfil_id", g.user.id).execute()
    return jsonify({"ok": True}), 200


# ──────────────────────────────────────────────
# OFERTAS / CONTRAPROPOSTAS
# ──────────────────────────────────────────────

@catalogo_bp.route("/<obra_id>/ofertas", methods=["POST"])
@require_auth
@require_role("interprete")
def criar_oferta(obra_id):
    data = request.get_json(force=True, silent=True) or {}

    try:
        valor_cents = int(data.get("valor_cents", 0))
        if valor_cents < 100:
            raise ValueError()
    except (ValueError, TypeError):
        abort(422, description="'valor_cents' deve ser inteiro >= 100.")

    mensagem = None
    if data.get("mensagem"):
        try:
            mensagem = sanitize_text(data["mensagem"], max_length=500)
        except ValueError as e:
            abort(422, description=str(e))

    sb = get_supabase()

    # Verifica que a obra existe e está publicada
    obra = sb.table("obras").select("id").eq("id", obra_id).eq("status", "publicada").execute()
    if not obra.data:
        abort(404, description="Obra não encontrada ou não publicada.")

    # Verifica se já existe oferta pendente do mesmo intérprete
    existente = (
        sb.table("ofertas")
        .select("id")
        .eq("obra_id", obra_id)
        .eq("interprete_id", g.user.id)
        .eq("status", "pendente")
        .execute()
    )
    if existente.data:
        abort(409, description="Você já possui uma oferta pendente para esta obra.")

    resp = sb.table("ofertas").insert({
        "obra_id":       obra_id,
        "interprete_id": g.user.id,
        "valor_cents":   valor_cents,
        "mensagem":      mensagem,
        "status":        "pendente",
    }).execute()

    return jsonify(resp.data[0]), 201


@catalogo_bp.route("/ofertas/<oferta_id>/responder", methods=["PATCH"])
@require_auth
@require_role("compositor")
def responder_oferta(oferta_id):
    data = request.get_json(force=True, silent=True) or {}
    novo_status = data.get("status")

    if novo_status not in ("aceita", "recusada"):
        abort(422, description="'status' deve ser 'aceita' ou 'recusada'.")

    sb = get_supabase()
    # RLS garante que só o titular da obra pode atualizar
    resp = (
        sb.table("ofertas")
        .update({"status": novo_status, "responded_at": "now()"})
        .eq("id", oferta_id)
        .eq("status", "pendente")
        .execute()
    )
    if not resp.data:
        abort(404, description="Oferta não encontrada ou já respondida.")
    return jsonify(resp.data[0]), 200


@catalogo_bp.route("/ofertas/recebidas", methods=["GET"])
@require_auth
@require_role("compositor")
def ofertas_recebidas():
    """Ofertas recebidas em obras do compositor autenticado."""
    sb = get_supabase()
    resp = (
        sb.table("ofertas")
        .select("*, obras(nome), perfis!interprete_id(nome, avatar_url)")
        .in_("obra_id",
             [r["id"] for r in
              sb.table("obras").select("id").eq("titular_id", g.user.id).execute().data or []]
             )
        .order("created_at", desc=True)
        .execute()
    )
    return jsonify(resp.data or []), 200


@catalogo_bp.route("/ofertas/enviadas", methods=["GET"])
@require_auth
@require_role("interprete")
def ofertas_enviadas():
    sb = get_supabase()
    resp = (
        sb.table("ofertas")
        .select("*, obras(nome, preco_cents)")
        .eq("interprete_id", g.user.id)
        .order("created_at", desc=True)
        .execute()
    )
    return jsonify(resp.data or []), 200
