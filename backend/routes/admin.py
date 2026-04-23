"""Routes: /api/admin — só administradores"""
from flask import Blueprint, jsonify, request, g, abort
from middleware.auth import require_auth
from db.supabase_client import get_supabase

admin_bp = Blueprint("admin", __name__)


def _check_admin():
    sb = get_supabase()
    r = sb.table("perfis").select("role").eq("id", g.user.id).single().execute()
    if not r.data or r.data.get("role") != "administrador":
        abort(403, description="Acesso restrito a administradores.")


@admin_bp.route("/bi/resumo", methods=["GET"])
@require_auth
def resumo_geral():
    _check_admin()
    sb = get_supabase()

    obras_total = sb.table("obras").select("id", count="exact").execute()
    obras_pub   = sb.table("obras").select("id", count="exact").eq("status", "publicada").execute()
    perfis      = sb.table("perfis").select("id, role", count="exact").execute()

    perfis_data = perfis.data or []
    n_compositores = sum(1 for p in perfis_data if p.get("role") == "compositor")
    n_interpretes  = sum(1 for p in perfis_data if p.get("role") == "interprete")

    trans = sb.table("transacoes").select("valor_cents, plataforma_cents, liquido_cents").eq("status", "confirmada").execute()
    trans_data = trans.data or []

    receita_bruta      = sum(t.get("valor_cents") or 0 for t in trans_data)
    receita_plataforma = sum(t.get("plataforma_cents") or 0 for t in trans_data)
    receita_compositores = sum(t.get("liquido_cents") or 0 for t in trans_data)

    ofertas_pendentes = sb.table("ofertas").select("id", count="exact").eq("status", "pendente").execute()

    return jsonify({
        "total_obras":             obras_total.count or 0,
        "obras_publicadas":        obras_pub.count or 0,
        "total_usuarios":          perfis.count or 0,
        "total_compositores":      n_compositores,
        "total_interpretes":       n_interpretes,
        "total_vendas":            len(trans_data),
        "receita_bruta_cents":     receita_bruta,
        "receita_plataforma_cents": receita_plataforma,
        "receita_compositores_cents": receita_compositores,
        "ofertas_pendentes":       ofertas_pendentes.count or 0,
    }), 200


@admin_bp.route("/bi/generos", methods=["GET"])
@require_auth
def generos_populares():
    _check_admin()
    sb = get_supabase()
    return jsonify(sb.table("bi_generos_populares").select("*").execute().data or []), 200


@admin_bp.route("/bi/volume", methods=["GET"])
@require_auth
def volume_transacional():
    _check_admin()
    sb = get_supabase()
    dias = min(int(request.args.get("dias", 30)), 365)
    return jsonify(sb.table("bi_volume_transacional").select("*").limit(dias * 4).execute().data or []), 200


@admin_bp.route("/bi/auditoria", methods=["GET"])
@require_auth
def auditoria_splits():
    _check_admin()
    sb = get_supabase()
    page     = max(1, int(request.args.get("page", 1)))
    per_page = min(100, int(request.args.get("per_page", 50)))
    offset   = (page - 1) * per_page
    return jsonify(sb.table("bi_auditoria_splits").select("*").range(offset, offset + per_page - 1).execute().data or []), 200

@admin_bp.route("/saques", methods=["GET"])
@require_auth
def listar_saques():
    _check_admin()
    sb = get_supabase()
    status = request.args.get("status")
    query = (
        sb.table("saques")
        .select("*, perfis(nome, nome_artistico, email)")
        .order("created_at", desc=True)
        .limit(100)
    )
    if status:
        query = query.eq("status", status)
    resp = query.execute()
    return jsonify(resp.data or []), 200


@admin_bp.route("/saques/<saque_id>/aprovar", methods=["POST"])
@require_auth
def aprovar_saque_admin(saque_id):
    _check_admin()
    data = request.get_json(force=True, silent=True) or {}
    acao = data.get("acao")  # pago | processando | rejeitado
    motivo = data.get("motivo")

    if acao not in ("pago", "processando", "rejeitado"):
        abort(422, description="Acao invalida.")

    sb = get_supabase()
    try:
        sb.rpc("aprovar_saque", {
            "p_saque_id": saque_id,
            "p_acao":     acao,
            "p_motivo":   motivo,
        }).execute()
    except Exception as e:
        abort(500, description=f"Erro ao aprovar saque: {str(e)}")

    return jsonify({"ok": True, "acao": acao}), 200


# ═══════════════════════════════════════════════════════════
# AUDIT LOGS — listagem global pra admin
# ═══════════════════════════════════════════════════════════
@admin_bp.route("/audit-logs", methods=["GET"])
@require_auth
def listar_audit_logs():
    _check_admin()
    sb = get_supabase()

    limite      = min(int(request.args.get("limit", 100)), 500)
    user_id     = request.args.get("user_id")
    action      = request.args.get("action")
    entity_type = request.args.get("entity_type")

    q = sb.table("audit_logs").select("*").order("created_at", desc=True).limit(limite)
    if user_id:     q = q.eq("user_id", user_id)
    if action:      q = q.eq("action", action)
    if entity_type: q = q.eq("entity_type", entity_type)

    r = q.execute()
    return jsonify(r.data or []), 200


# ═══════════════════════════════════════════════════════════
# VER COMO ADMIN — visão completa de qualquer perfil
# ═══════════════════════════════════════════════════════════
@admin_bp.route("/perfis/<perfil_id>/visao", methods=["GET"])
@require_auth
def visao_perfil(perfil_id):
    _check_admin()
    sb = get_supabase()

    perfil = sb.table("perfis").select("*").eq("id", perfil_id).maybe_single().execute()
    if not perfil or not perfil.data:
        abort(404, description="Perfil não encontrado")

    obras_aut = sb.table("obras_autores").select("obra_id").eq("perfil_id", perfil_id).execute()
    obras_ids = list({o["obra_id"] for o in (obras_aut.data or [])})
    obras = []
    if obras_ids:
        try:
            obras = sb.table("obras").select("id,titulo,publicada,created_at").in_("id", obras_ids).execute().data or []
        except Exception:
            obras = []

    contratos = []
    try:
        contratos = sb.table("contracts_edicao").select("id,status,created_at,obra_id") \
            .or_(f"autor_id.eq.{perfil_id},publisher_id.eq.{perfil_id}") \
            .order("created_at", desc=True).limit(50).execute().data or []
    except Exception:
        pass

    ganhos_cents = 0
    try:
        rep = sb.table("repasses").select("valor_cents,status").eq("perfil_id", perfil_id).execute()
        ganhos_cents = sum(r.get("valor_cents", 0) for r in (rep.data or []) if r.get("status") == "enviado")
    except Exception:
        pass

    return jsonify({
        "perfil":    perfil.data,
        "obras":     obras,
        "contratos": contratos,
        "ganhos_cents": ganhos_cents,
    }), 200


# ═══════════════════════════════════════════════════════════
# LISTAGEM E DASHBOARD DE EDITORAS (admin only)
# ═══════════════════════════════════════════════════════════
@admin_bp.route("/publishers", methods=["GET"])
@require_auth
def listar_publishers():
    """Lista todos os perfis com role=publisher (editoras), com contagens básicas."""
    _check_admin()
    sb = get_supabase()

    pubs = sb.table("perfis") \
        .select("id, nome, nome_artistico, razao_social, email, avatar_url, created_at, cadastro_completo") \
        .eq("role", "publisher") \
        .order("created_at", desc=True) \
        .execute()
    pubs_data = pubs.data or []

    # Contagens agregadas (best-effort)
    resumo = []
    for p in pubs_data:
        pid = p["id"]
        try:
            n_obras = sb.table("obras").select("id", count="exact").eq("publisher_id", pid).execute().count or 0
        except Exception:
            n_obras = 0
        try:
            n_agreg = sb.table("perfis").select("id", count="exact").eq("publisher_id", pid).execute().count or 0
        except Exception:
            n_agreg = 0
        try:
            n_contr = sb.table("contracts_edicao").select("id", count="exact").eq("publisher_id", pid).execute().count or 0
        except Exception:
            n_contr = 0
        resumo.append({**p,
                       "total_obras":     n_obras,
                       "total_agregados": n_agreg,
                       "total_contratos": n_contr})
    return jsonify(resumo), 200


@admin_bp.route("/publishers/<publisher_id>/dashboard", methods=["GET"])
@require_auth
def publisher_dashboard_admin(publisher_id):
    """Dashboard completo de uma editora — visão admin."""
    _check_admin()
    sb = get_supabase()

    perfil = sb.table("perfis").select("*").eq("id", publisher_id).maybe_single().execute()
    if not perfil or not perfil.data:
        abort(404, description="Editora não encontrada")
    if perfil.data.get("role") != "publisher":
        abort(400, description="Perfil informado não é uma editora")

    # Obras da editora
    obras = []
    try:
        obras = sb.table("obras") \
            .select("id, titulo, publicada, status, preco_cents, created_at, genero") \
            .eq("publisher_id", publisher_id) \
            .order("created_at", desc=True).execute().data or []
    except Exception:
        pass
    obras_ids = [o["id"] for o in obras]

    # Agregados (compositores ligados à editora)
    agregados = []
    try:
        agregados = sb.table("perfis") \
            .select("id, nome, nome_artistico, email, avatar_url, nivel, created_at") \
            .eq("publisher_id", publisher_id) \
            .order("created_at", desc=True).execute().data or []
    except Exception:
        pass

    # Contratos de edição
    contratos = []
    try:
        contratos = sb.table("contracts_edicao") \
            .select("id, status, created_at, autor_id, obra_id") \
            .eq("publisher_id", publisher_id) \
            .order("created_at", desc=True).execute().data or []
    except Exception:
        pass
    contratos_assinados = [c for c in contratos if c.get("status") == "assinado"]
    contratos_pendentes = [c for c in contratos if c.get("status") in ("pendente", "assinado_parcial")]

    # Faturamento — soma de transações pagas das obras da editora
    faturamento_cents = 0
    transacoes = []
    if obras_ids:
        try:
            tx = sb.table("transacoes") \
                .select("id, valor_cents, status, created_at, obra_id") \
                .in_("obra_id", obras_ids) \
                .order("created_at", desc=True).limit(200).execute().data or []
            transacoes = tx
            faturamento_cents = sum(t.get("valor_cents", 0) for t in tx if t.get("status") == "pago")
        except Exception:
            pass

    return jsonify({
        "perfil":                perfil.data,
        "obras":                 obras,
        "agregados":             agregados,
        "contratos":             contratos,
        "transacoes":            transacoes[:50],
        "totais": {
            "obras":               len(obras),
            "obras_publicadas":    len([o for o in obras if o.get("publicada") or o.get("status") == "publicada"]),
            "agregados":           len(agregados),
            "contratos":           len(contratos),
            "contratos_assinados": len(contratos_assinados),
            "contratos_pendentes": len(contratos_pendentes),
            "faturamento_cents":   faturamento_cents,
            "fee_devido_cents":    int(faturamento_cents * 0.05),
        },
    }), 200


# ═══════════════════════════════════════════════════════════
# EXCLUSÃO DEFINITIVA DE USUÁRIO (admin only)
# Apaga todos os rastros do usuário no banco e no auth.users.
# Uso: DELETE /api/admin/perfis/<perfil_id>?confirmacao=EXCLUIR
# ═══════════════════════════════════════════════════════════
@admin_bp.route("/perfis/<perfil_id>", methods=["DELETE"])
@admin_bp.route("/perfis/<perfil_id>/excluir", methods=["POST"])
@require_auth
def excluir_perfil_definitivo(perfil_id):
    _check_admin()

    # Confirmação dupla para evitar exclusão acidental
    confirmacao = request.args.get("confirmacao") or (request.get_json(silent=True) or {}).get("confirmacao")
    if confirmacao != "EXCLUIR":
        abort(400, description="Confirmação ausente. Envie ?confirmacao=EXCLUIR para confirmar.")

    # Não pode excluir a si mesmo
    if str(perfil_id) == str(g.user.id):
        abort(400, description="Você não pode excluir seu próprio usuário.")

    sb = get_supabase()

    # Verifica que o perfil existe e captura o role (não permitir excluir outro admin)
    perfil_resp = sb.table("perfis").select("id, role, email").eq("id", perfil_id).maybe_single().execute()
    if not perfil_resp or not perfil_resp.data:
        abort(404, description="Perfil não encontrado.")
    if perfil_resp.data.get("role") == "administrador":
        abort(403, description="Não é permitido excluir outro administrador por este endpoint.")

    apagados = {}
    erros = {}

    # Lista de (tabela, coluna) para limpar referências.
    # Algumas tabelas podem não existir — capturamos o erro silenciosamente.
    targets = [
        # Engajamento e histórico
        ("favoritos",                "perfil_id"),
        ("historico_escuta",         "perfil_id"),
        ("play_events",              "perfil_id"),
        ("obra_analytics",           "perfil_id"),
        ("comentarios",              "perfil_id"),
        # Financeiro
        ("repasses",                 "perfil_id"),
        ("saques",                   "perfil_id"),
        ("wallets",                  "perfil_id"),
        ("pagamentos_compositores",  "perfil_id"),
        ("transacoes",               "comprador_id"),
        ("transacoes",               "vendedor_id"),
        # Contratos / ofertas
        ("ofertas",                  "comprador_id"),
        ("ofertas",                  "vendedor_id"),
        ("contract_signers",         "perfil_id"),
        ("contract_events",          "perfil_id"),
        ("contracts_edicao",         "autor_id"),
        ("contracts_edicao",         "publisher_id"),
        ("contracts",                "autor_id"),
        ("contracts",                "comprador_id"),
        # Contato / mensagens
        ("contato_mensagens",        "perfil_id"),
        # Audit log
        ("audit_logs",               "user_id"),
    ]

    for tabela, coluna in targets:
        try:
            r = sb.table(tabela).delete().eq(coluna, perfil_id).execute()
            qtd = len(r.data) if getattr(r, "data", None) else 0
            apagados[f"{tabela}.{coluna}"] = qtd
        except Exception as e:
            erros[f"{tabela}.{coluna}"] = str(e)[:120]

    # Coautorias: apagar pelo perfil_id e também pegar as obras onde ele é o único autor
    obras_solo = []
    try:
        coa = sb.table("coautorias").select("obra_id").eq("perfil_id", perfil_id).execute()
        obras_ids_coa = list({c["obra_id"] for c in (coa.data or [])})
        for oid in obras_ids_coa:
            try:
                outros = sb.table("coautorias").select("perfil_id").eq("obra_id", oid).neq("perfil_id", perfil_id).limit(1).execute()
                if not (outros.data or []):
                    obras_solo.append(oid)
            except Exception:
                pass
        sb.table("coautorias").delete().eq("perfil_id", perfil_id).execute()
        apagados["coautorias.perfil_id"] = len(coa.data or [])
    except Exception as e:
        erros["coautorias"] = str(e)[:120]

    # obras_autores: mesmo tratamento
    try:
        oa = sb.table("obras_autores").select("obra_id").eq("perfil_id", perfil_id).execute()
        obras_ids_oa = list({o["obra_id"] for o in (oa.data or [])})
        for oid in obras_ids_oa:
            if oid in obras_solo:
                continue
            try:
                outros = sb.table("obras_autores").select("perfil_id").eq("obra_id", oid).neq("perfil_id", perfil_id).limit(1).execute()
                if not (outros.data or []):
                    obras_solo.append(oid)
            except Exception:
                pass
        sb.table("obras_autores").delete().eq("perfil_id", perfil_id).execute()
        apagados["obras_autores.perfil_id"] = len(oa.data or [])
    except Exception as e:
        erros["obras_autores"] = str(e)[:120]

    # Apagar obras onde ele era titular (independentemente de coautores)
    try:
        ot = sb.table("obras").select("id").eq("titular_id", perfil_id).execute()
        for o in (ot.data or []):
            if o["id"] not in obras_solo:
                obras_solo.append(o["id"])
    except Exception:
        pass

    # Apagar as obras "órfãs" (sem outros autores ou cujo titular é o usuário)
    obras_apagadas = 0
    for oid in obras_solo:
        # limpa dependências da obra primeiro
        for tabela, coluna in [
            ("favoritos",        "obra_id"),
            ("historico_escuta", "obra_id"),
            ("play_events",      "obra_id"),
            ("obra_analytics",   "obra_id"),
            ("comentarios",      "obra_id"),
            ("ofertas",          "obra_id"),
            ("transacoes",       "obra_id"),
            ("contracts_edicao", "obra_id"),
            ("contracts",        "obra_id"),
            ("coautorias",       "obra_id"),
            ("obras_autores",    "obra_id"),
        ]:
            try:
                sb.table(tabela).delete().eq(coluna, oid).execute()
            except Exception:
                pass
        try:
            sb.table("obras").delete().eq("id", oid).execute()
            obras_apagadas += 1
        except Exception as e:
            erros[f"obras:{oid}"] = str(e)[:120]
    apagados["obras"] = obras_apagadas

    # Finalmente, apaga o registro em perfis
    try:
        sb.table("perfis").delete().eq("id", perfil_id).execute()
        apagados["perfis"] = 1
    except Exception as e:
        erros["perfis"] = str(e)[:200]

    # Apaga o usuário do auth.users (Supabase Auth)
    auth_apagado = False
    try:
        sb.auth.admin.delete_user(perfil_id)
        auth_apagado = True
    except Exception as e:
        erros["auth.users"] = str(e)[:200]

    # Audit log da exclusão (se a tabela ainda existir)
    try:
        sb.table("audit_logs").insert({
            "user_id":     g.user.id,
            "action":      "delete_user",
            "entity_type": "perfil",
            "entity_id":   perfil_id,
            "metadata":    {"alvo_email": perfil_resp.data.get("email"), "apagados": apagados, "erros": erros},
        }).execute()
    except Exception:
        pass

    return jsonify({
        "ok":            True,
        "perfil_id":     perfil_id,
        "auth_apagado":  auth_apagado,
        "apagados":      apagados,
        "erros":         erros,
    }), 200


  # ═══════════════════════════════════════════════════════════
  # PAINEL + HISTÓRICO DE SAQUES OTP (admin only)
  # ═══════════════════════════════════════════════════════════

@admin_bp.route("/saques/painel", methods=["GET"])
@require_auth
def painel_saques():
    """Contagens por status e totais do dia."""
    _check_admin()
    sb = get_supabase()
    from datetime import datetime, timezone
    hoje_inicio = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    todos = sb.table("saques").select("status, valor_cents, created_at").execute().data or []
    contagens = {}
    for s in todos:
        st = s.get("status", "desconhecido")
        contagens[st] = contagens.get(st, 0) + 1
    pagos_hoje     = [s for s in todos if s.get("status") == "pago"      and (s.get("created_at") or "") >= hoje_inicio]
    cancelados_hoje = [s for s in todos if s.get("status") == "cancelado" and (s.get("created_at") or "") >= hoje_inicio]
    contagens["pago_hoje"]        = len(pagos_hoje)
    contagens["cancelado_hoje"]   = len(cancelados_hoje)
    contagens["total_hoje_cents"] = sum(s.get("valor_cents", 0) for s in pagos_hoje)
    return jsonify({"contagens": contagens}), 200


@admin_bp.route("/saques/<saque_id>/forcar-liberar", methods=["POST"])
@require_auth
def forcar_liberar_saque(saque_id):
    """Força liberação imediata de saque aguardando_liberacao."""
    _check_admin()
    sb = get_supabase()
    s = sb.table("saques").select("status").eq("id", saque_id).maybe_single().execute()
    if not s or not s.data:
        abort(404, description="Saque não encontrado.")
    if s.data.get("status") != "aguardando_liberacao":
        abort(422, description=f"Status atual: '{s.data.get('status')}'. Só é possível forçar saques em 'aguardando_liberacao'.")
    from datetime import datetime, timezone
    sb.table("saques").update({"liberar_em": datetime.now(timezone.utc).isoformat()}).eq("id", saque_id).execute()
    try:
        sb.rpc("saques_a_liberar", {"p_limit": 1}).execute()
    except Exception:
        pass
    return jsonify({"ok": True, "mensagem": "Saque marcado para liberação imediata. O próximo ciclo do cron irá processar."}), 200


@admin_bp.route("/saques/<saque_id>/cancelar-admin", methods=["POST"])
@require_auth
def cancelar_saque_admin(saque_id):
    """Admin cancela saque e devolve o valor à wallet."""
    _check_admin()
    data = request.get_json(force=True, silent=True) or {}
    motivo = (data.get("motivo") or "").strip()
    if not motivo:
        abort(422, description="Informe o motivo do cancelamento.")
    sb = get_supabase()
    s = sb.table("saques").select("status").eq("id", saque_id).maybe_single().execute()
    if not s or not s.data:
        abort(404, description="Saque não encontrado.")
    if s.data.get("status") not in ("pendente_otp", "aguardando_liberacao"):
        abort(422, description=f"Não é possível cancelar saque com status '{s.data.get('status')}'.")
    from datetime import datetime, timezone
    sb.table("saques").update({
        "status":          "cancelado",
        "cancelado_em":    datetime.now(timezone.utc).isoformat(),
        "cancelado_motivo": f"[Admin] {motivo}",
    }).eq("id", saque_id).execute()
    return jsonify({"ok": True, "mensagem": "Saque cancelado pelo administrador."}), 200


@admin_bp.route("/saques/historico", methods=["GET"])
@require_auth
def historico_saques():
    """Histórico paginado de saques com filtros de data, status e busca textual."""
    _check_admin()
    sb = get_supabase()

    q_text      = (request.args.get("q") or "").strip()
    status_fil  = request.args.get("status", "")
    data_inicio = request.args.get("data_inicio", "")
    data_fim    = request.args.get("data_fim", "")
    limite      = min(int(request.args.get("limit", 200)), 1000)

    query = (
        sb.table("saques")
        .select("id, perfil_id, valor_cents, status, created_at, confirmado_em, liberar_em, cancelado_em, cancelado_motivo, otp_attempts, otp_expires_at, perfis(nome, nome_artistico, email)")
        .order("created_at", desc=True)
        .limit(limite)
    )

    if status_fil:
        query = query.eq("status", status_fil)
    if data_inicio:
        query = query.gte("created_at", data_inicio)
    if data_fim:
        query = query.lte("created_at", data_fim)

    result = query.execute()
    saques = result.data or []

    # Filtro textual por nome / e-mail (feito no Python porque Supabase não faz join+ilike facilmente)
    if q_text:
        ql = q_text.lower()
        saques = [
            s for s in saques
            if ql in (s.get("perfis") or {}).get("email", "").lower()
            or ql in (s.get("perfis") or {}).get("nome", "").lower()
            or ql in (s.get("perfis") or {}).get("nome_artistico", "").lower()
        ]

    return jsonify(saques), 200
