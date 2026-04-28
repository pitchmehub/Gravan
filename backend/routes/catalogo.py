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
    apenas_pro = request.args.get("pro", "").lower() in ("1", "true", "yes")
    sort     = (request.args.get("sort") or "recente").lower()
    page     = max(1, int(request.args.get("page", 1)))
    per_page = min(50, int(request.args.get("per_page", 20)))
    offset   = (page - 1) * per_page

    sb = get_supabase()

    # Mapeia ordenação aceita
    sort_map = {
        "recente":    ("created_at",  True),   # mais recentes primeiro
        "antiga":     ("created_at",  False),
        "preco_asc":  ("preco_cents", False),  # mais baratas primeiro
        "preco_desc": ("preco_cents", True),
        "nome":       ("nome",        False),
    }
    order_col, order_desc = sort_map.get(sort, sort_map["recente"])

    query = (
        sb.table("catalogo_publico")
        .select("*")
        .order(order_col, desc=order_desc)
        .range(offset, offset + per_page - 1)
    )
    if genero:
        query = query.eq("genero", genero)
    if busca:
        query = query.ilike("nome", f"%{busca}%")

    if apenas_pro:
        # busca ids dos perfis PRO ativos (assinatura vigente)
        pro_resp = (
            sb.table("perfis")
            .select("id")
            .eq("plano", "PRO")
            .in_("status_assinatura", ["ativa", "cancelada", "past_due"])
            .execute()
        )
        pro_ids = [p["id"] for p in (pro_resp.data or [])]
        if not pro_ids:
            return jsonify([]), 200
        query = query.in_("titular_id", pro_ids)

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
        .select("*, perfis(nome, avatar_url)")
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

from datetime import datetime, timezone
from services.ofertas import (
    deadline_pagamento_iso,
    publishers_da_obra,
    validar_nova_oferta,
    notificar_compositor_nova_oferta,
    notificar_interprete_resposta,
    notificar_resposta_contraproposta,
    expirar_pendentes,
    _expirar_se_vencida,
    _expires_at_iso,
    OFERTA_VALIDADE_HORAS,
)


@catalogo_bp.route("/<obra_id>/ofertas", methods=["POST"])
@require_auth
def criar_oferta(obra_id):
    """
    Body:
      valor_cents: int  (obrigatório)
      tipo: 'padrao' | 'exclusividade'  (default padrao)
      mensagem: str (opcional)
    """
    data = request.get_json(force=True, silent=True) or {}

    try:
        valor_cents = int(data.get("valor_cents", 0))
        if valor_cents < 100:
            raise ValueError()
    except (ValueError, TypeError):
        abort(422, description="'valor_cents' deve ser inteiro >= 100.")

    tipo = (data.get("tipo") or "padrao").strip().lower()
    if tipo not in ("padrao", "exclusividade"):
        abort(422, description="'tipo' deve ser 'padrao' ou 'exclusividade'.")

    mensagem = None
    if data.get("mensagem"):
        try:
            mensagem = sanitize_text(data["mensagem"], max_length=500)
        except ValueError as e:
            abort(422, description=str(e))

    sb = get_supabase()

    obra_resp = sb.table("obras").select(
        "id, nome, preco_cents, status, titular_id, is_exclusive, editora_terceira_id"
    ).eq("id", obra_id).single().execute()
    obra = obra_resp.data
    if not obra:
        abort(404, description="Obra não encontrada.")
    if obra["titular_id"] == g.user.id:
        abort(422, description="Você não pode ofertar em uma obra de sua autoria.")

    titular = sb.table("perfis").select(
        "id, nome, plano, status_assinatura"
    ).eq("id", obra["titular_id"]).single().execute().data or {}

    erro = validar_nova_oferta(obra, titular, valor_cents, tipo)
    if erro:
        abort(422, description=erro)

    # Bloqueia múltiplas pendentes do mesmo intérprete na mesma obra
    expirar_pendentes()
    existente = (
        sb.table("ofertas").select("id")
        .eq("obra_id", obra_id)
        .eq("interprete_id", g.user.id)
        .eq("status", "pendente")
        .execute()
    )
    if existente.data:
        abort(409, description="Você já possui uma oferta pendente para esta obra.")

    novo = sb.table("ofertas").insert({
        "obra_id":       obra_id,
        "interprete_id": g.user.id,
        "valor_cents":   valor_cents,
        "mensagem":      mensagem,
        "status":        "pendente",
        "tipo":          tipo,
        "aguardando_resposta_de": "compositor",
        "expires_at":    _expires_at_iso(),
    }).execute().data[0]

    interprete = sb.table("perfis").select("nome").eq("id", g.user.id).single().execute().data or {}
    notificar_compositor_nova_oferta(novo, obra, interprete.get("nome") or "Intérprete")

    return jsonify(novo), 201


@catalogo_bp.route("/ofertas/<oferta_id>/responder", methods=["PATCH"])
@require_auth
@require_role("compositor")
def responder_oferta(oferta_id):
    """
    Body:
      status: 'aceita' | 'recusada'
    Apenas o compositor (titular da obra) pode responder.
    Marca a oferta e notifica o intérprete.
    """
    data = request.get_json(force=True, silent=True) or {}
    novo_status = data.get("status")
    if novo_status not in ("aceita", "recusada"):
        abort(422, description="'status' deve ser 'aceita' ou 'recusada'.")

    sb = get_supabase()
    of = sb.table("ofertas").select("*").eq("id", oferta_id).single().execute().data
    if not of:
        abort(404, description="Oferta não encontrada.")
    of = _expirar_se_vencida(of)
    if of["status"] != "pendente":
        abort(409, description=f"Oferta em status '{of['status']}', não pode mais ser respondida.")
    if of.get("aguardando_resposta_de") != "compositor":
        abort(409, description="Esta oferta aguarda resposta do intérprete.")

    obra = sb.table("obras").select(
        "id, nome, titular_id, editora_terceira_id"
    ).eq("id", of["obra_id"]).single().execute().data or {}
    if obra.get("titular_id") != g.user.id:
        abort(403, description="Apenas o titular da obra pode responder esta oferta.")

    update_payload = {
        "status": novo_status,
        "responded_at": datetime.now(timezone.utc).isoformat(),
    }
    # Ao aceitar, abre janela de 72h para o comprador assinar/pagar
    # (substitui o expires_at original de 48h da fase de negociação).
    if novo_status == "aceita":
        update_payload["expires_at"] = deadline_pagamento_iso()

    upd = sb.table("ofertas").update(update_payload).eq("id", oferta_id).execute().data[0]

    notificar_interprete_resposta(upd, obra, novo_status)
    return jsonify(upd), 200


@catalogo_bp.route("/ofertas/<oferta_id>/contra-propor", methods=["POST"])
@require_auth
@require_role("compositor")
def contra_propor_oferta(oferta_id):
    """
    Compositor sugere outro valor. A oferta original vai para
    'contra_proposta' (encerrada) e uma nova oferta é criada com
    contraproposta_de_id = oferta_original, aguardando resposta do intérprete.
    Body: { valor_cents: int, mensagem?: str }
    """
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
    of = sb.table("ofertas").select("*").eq("id", oferta_id).single().execute().data
    if not of:
        abort(404, description="Oferta não encontrada.")
    of = _expirar_se_vencida(of)
    if of["status"] != "pendente":
        abort(409, description=f"Oferta em status '{of['status']}', não pode mais ser respondida.")
    if of.get("aguardando_resposta_de") != "compositor":
        abort(409, description="Esta oferta aguarda resposta do intérprete.")

    obra = sb.table("obras").select(
        "id, nome, preco_cents, titular_id, is_exclusive, editora_terceira_id"
    ).eq("id", of["obra_id"]).single().execute().data or {}
    if obra.get("titular_id") != g.user.id:
        abort(403, description="Apenas o titular da obra pode contra-propor.")

    # Para contraproposta, exigimos pelo menos o piso da modalidade da oferta original
    titular = sb.table("perfis").select(
        "id, plano, status_assinatura"
    ).eq("id", obra["titular_id"]).single().execute().data or {}
    erro = validar_nova_oferta(obra, titular, valor_cents, of.get("tipo", "padrao"))
    if erro:
        abort(422, description=erro)

    # Marca a original como contra_proposta (resposta dada)
    sb.table("ofertas").update({
        "status": "contra_proposta",
        "responded_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", of["id"]).execute()

    # Cria a nova oferta como contraproposta encadeada (agora aguardando intérprete)
    nova = sb.table("ofertas").insert({
        "obra_id":       of["obra_id"],
        "interprete_id": of["interprete_id"],
        "valor_cents":   valor_cents,
        "mensagem":      mensagem,
        "status":        "pendente",
        "tipo":          of.get("tipo", "padrao"),
        "aguardando_resposta_de": "interprete",
        "expires_at":    _expires_at_iso(),
        "contraproposta_de_id": of["id"],
    }).execute().data[0]

    notificar_interprete_resposta(nova, obra, "contra_proposta")
    # Notifica também o intérprete (já feito acima) — editoras já entram pela função
    return jsonify(nova), 201


@catalogo_bp.route("/ofertas/<oferta_id>/responder-contraproposta", methods=["PATCH"])
@require_auth
def responder_contraproposta(oferta_id):
    """
    Intérprete responde a uma contraproposta do compositor.
    Body: { status: 'aceita' | 'recusada' }
    Aceitar = libera o checkout (frontend redireciona para /comprar?oferta_id=X).
    """
    data = request.get_json(force=True, silent=True) or {}
    novo_status = data.get("status")
    if novo_status not in ("aceita", "recusada"):
        abort(422, description="'status' deve ser 'aceita' ou 'recusada'.")

    sb = get_supabase()
    of = sb.table("ofertas").select("*").eq("id", oferta_id).single().execute().data
    if not of:
        abort(404, description="Oferta não encontrada.")
    of = _expirar_se_vencida(of)
    if of["status"] != "pendente":
        abort(409, description=f"Oferta em status '{of['status']}'.")
    if of.get("aguardando_resposta_de") != "interprete":
        abort(409, description="Esta oferta aguarda resposta do compositor, não sua.")
    if of["interprete_id"] != g.user.id:
        abort(403, description="Apenas o intérprete que recebeu a contraproposta pode respondê-la.")

    update_payload = {
        "status": novo_status,
        "responded_at": datetime.now(timezone.utc).isoformat(),
    }
    # Quando aceita, abre janela de pagamento de 72h (mesma regra do
    # aceite feito pelo compositor em uma oferta normal).
    if novo_status == "aceita":
        update_payload["expires_at"] = deadline_pagamento_iso()

    upd = sb.table("ofertas").update(update_payload).eq("id", oferta_id).execute().data[0]

    obra = sb.table("obras").select(
        "id, nome, titular_id, editora_terceira_id"
    ).eq("id", of["obra_id"]).single().execute().data or {}

    # Notifica compositor titular + editoras envolvidas (intérprete não recebe;
    # frontend já dá feedback imediato a ele).
    notificar_resposta_contraproposta(upd, obra, novo_status)

    # Quando aceita, devolve o caminho do checkout para o frontend redirecionar.
    resp = dict(upd)
    if novo_status == "aceita":
        resp["checkout_redirect"] = f"/comprar/{obra['id']}?oferta_id={upd['id']}"
    return jsonify(resp), 200


@catalogo_bp.route("/ofertas/recebidas", methods=["GET"])
@require_auth
@require_role("compositor")
def ofertas_recebidas():
    """Ofertas em obras do compositor autenticado.
    Inclui o histórico de contrapropostas de cada cadeia."""
    sb = get_supabase()
    expirar_pendentes()
    obras_ids = [r["id"] for r in
                 sb.table("obras").select("id").eq("titular_id", g.user.id).execute().data or []]
    if not obras_ids:
        return jsonify([]), 200
    resp = (
        sb.table("ofertas")
        .select("*, obras!ofertas_obra_id_fkey(nome, preco_cents, is_exclusive), perfis!interprete_id(nome, avatar_url)")
        .in_("obra_id", obras_ids)
        .order("created_at", desc=True)
        .execute()
    )
    return jsonify(resp.data or []), 200


@catalogo_bp.route("/ofertas/enviadas", methods=["GET"])
@require_auth
def ofertas_enviadas():
    sb = get_supabase()
    expirar_pendentes()
    resp = (
        sb.table("ofertas")
        .select("*, obras!ofertas_obra_id_fkey(nome, preco_cents, is_exclusive)")
        .eq("interprete_id", g.user.id)
        .order("created_at", desc=True)
        .execute()
    )
    return jsonify(resp.data or []), 200


@catalogo_bp.route("/ofertas/editora", methods=["GET"])
@require_auth
def ofertas_editora():
    """
    Ofertas em obras que o usuário (editora) edita — seja como editora-mãe
    (perfis.publisher_id dos compositores agregados) ou como editora terceira
    (obras.editora_terceira_id).

    Visão somente leitura: a editora acompanha mas não decide; quem aceita,
    recusa ou contra-propõe é o compositor titular.
    """
    sb = get_supabase()
    expirar_pendentes()
    me = g.user.id

    # 1) IDs de obras onde sou editora-mãe (titular agregado)
    agregados = sb.table("perfis").select("id").eq("publisher_id", me).execute().data or []
    agregados_ids = [a["id"] for a in agregados]

    obras_ids: set[str] = set()
    if agregados_ids:
        obras_agreg = (
            sb.table("obras").select("id")
            .in_("titular_id", agregados_ids).execute().data or []
        )
        obras_ids.update(o["id"] for o in obras_agreg)

    # 2) IDs de obras onde sou editora terceira
    obras_terc = (
        sb.table("obras").select("id")
        .eq("editora_terceira_id", me).execute().data or []
    )
    obras_ids.update(o["id"] for o in obras_terc)

    if not obras_ids:
        return jsonify([]), 200

    resp = (
        sb.table("ofertas")
        .select("*, obras!ofertas_obra_id_fkey(nome, preco_cents, is_exclusive, titular_id), perfis!interprete_id(nome, avatar_url)")
        .in_("obra_id", list(obras_ids))
        .order("created_at", desc=True)
        .execute()
    )
    return jsonify(resp.data or []), 200


@catalogo_bp.route("/ofertas/<oferta_id>", methods=["GET"])
@require_auth
def detalhe_oferta(oferta_id):
    """Detalhe de uma oferta — útil para a página de checkout
    confirmar valor/elegibilidade antes de pagar."""
    sb = get_supabase()
    of = (
        sb.table("ofertas")
        .select("*, obras!ofertas_obra_id_fkey(id, nome, titular_id, preco_cents, is_exclusive)")
        .eq("id", oferta_id).single().execute().data
    )
    if not of:
        abort(404)
    of = _expirar_se_vencida(of)

    # Visível para intérprete autor da oferta ou compositor titular da obra
    obra = of.get("obras") or {}
    if g.user.id != of["interprete_id"] and g.user.id != obra.get("titular_id"):
        abort(403)

    return jsonify(of), 200
