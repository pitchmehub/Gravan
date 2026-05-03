"""Routes: /api/admin — só administradores"""
from flask import Blueprint, jsonify, request, g, abort
from middleware.auth import require_auth
from db.supabase_client import get_supabase
from services.migrations_status import summary as migrations_summary
from app import limiter

admin_bp = Blueprint("admin", __name__)


def _check_admin():
    sb = get_supabase()
    r = sb.table("perfis").select("role").eq("id", g.user.id).single().execute()
    if not r.data or r.data.get("role") != "administrador":
        abort(403, description="Acesso restrito a administradores.")


@admin_bp.before_request
def _enforce_admin_on_all_routes():
    """
    Camada de segurança centralizada: toda rota do admin_bp exige
    JWT válido + papel 'administrador', independentemente de decoradores
    individuais. Impede que uma rota adicionada sem @require_auth fique exposta.
    """
    from middleware.auth import _get_cached_user, _cache_user
    from db.supabase_client import get_supabase as _gsb

    # CORS preflight: precisa retornar 2xx sem auth — Flask-CORS responde.
    if request.method == "OPTIONS":
        return None

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        abort(401, description="Token de autenticação ausente.")

    jwt = auth_header.split(" ", 1)[1]
    if len(jwt) < 20 or len(jwt) > 2000:
        abort(401, description="Token inválido.")

    user = _get_cached_user(jwt)
    if user is None:
        try:
            sb = _gsb()
            user_resp = sb.auth.get_user(jwt)
            if not user_resp or not user_resp.user:
                abort(401, description="Token inválido ou expirado.")
            user = user_resp.user
            _cache_user(jwt, user)
        except Exception:
            abort(401, description="Falha ao validar o token.")

    g.user = user
    g.jwt = jwt
    _check_admin()


@admin_bp.route("/migrations-status", methods=["GET"])
@require_auth
def migrations_status():
    """
    Retorna o status de cada migração SQL conhecida:
      - applied  → tabela/colunas detectadas no banco
      - missing  → migração ainda não rodada
      - unknown  → erro inesperado ao consultar (ver campo `error`)
    """
    _check_admin()
    return jsonify(migrations_summary()), 200


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


@admin_bp.route("/bi/extras", methods=["GET"])
@require_auth
def bi_extras():
    """
    Analíticos globais complementares: usuários (por papel, novos cadastros,
    plano PRO/STARTER), economia gerada pela assinatura PRO, receita por
    janela (7d / 30d / total), receita de assinatura, e ofertas (catálogo
    + licenciamento de terceiros) em todos os status. Pensado para popular
    o cabeçalho do painel Analíticos do admin com auto-refresh.
    """
    _check_admin()
    sb = get_supabase()

    from datetime import datetime, timedelta, timezone
    agora = datetime.now(timezone.utc)
    iso_7d  = (agora - timedelta(days=7)).isoformat()
    iso_30d = (agora - timedelta(days=30)).isoformat()

    # ── 1. Usuários por papel + novos cadastros ────────────────────
    perfis = (sb.table("perfis")
                .select("id, role, plano, status_assinatura, "
                        "assinatura_inicio, created_at")
                .execute()).data or []

    por_role = {}
    for p in perfis:
        r = p.get("role") or "sem_papel"
        por_role[r] = por_role.get(r, 0) + 1

    novos_7d  = sum(1 for p in perfis if (p.get("created_at") or "") >= iso_7d)
    novos_30d = sum(1 for p in perfis if (p.get("created_at") or "") >= iso_30d)

    pro_ativos     = sum(1 for p in perfis
                         if p.get("plano") == "PRO"
                         and p.get("status_assinatura") == "ativa")
    pro_past_due   = sum(1 for p in perfis
                         if p.get("plano") == "PRO"
                         and p.get("status_assinatura") == "past_due")
    starter_total  = sum(1 for p in perfis if p.get("plano") != "PRO")

    # ── 2. Transações + economia gerada pela assinatura PRO ───────
    # PRO paga 20% de fee; STARTER paga 25%. Para cada transação confirmada
    # de um titular PRO, a economia = (25% - 20%) × valor = 5% × valor.
    # Calculamos comparando o que seria cobrado a 25% vs o que foi cobrado.
    trans = (sb.table("transacoes")
               .select("id, valor_cents, plataforma_cents, liquido_cents, "
                       "status, created_at")
               .eq("status", "confirmada")
               .execute()).data or []

    receita_total      = sum(int(t.get("valor_cents") or 0) for t in trans)
    plataforma_total   = sum(int(t.get("plataforma_cents") or 0) for t in trans)
    economia_assinatura_total = sum(
        max(0, int(round((t.get("valor_cents") or 0) * 0.25)) - int(t.get("plataforma_cents") or 0))
        for t in trans
    )

    receita_7d = sum(int(t.get("valor_cents") or 0)
                     for t in trans if (t.get("created_at") or "") >= iso_7d)
    receita_30d = sum(int(t.get("valor_cents") or 0)
                      for t in trans if (t.get("created_at") or "") >= iso_30d)
    economia_30d = sum(
        max(0, int(round((t.get("valor_cents") or 0) * 0.25)) - int(t.get("plataforma_cents") or 0))
        for t in trans if (t.get("created_at") or "") >= iso_30d
    )

    transacoes_total = len(trans)
    transacoes_30d   = sum(1 for t in trans if (t.get("created_at") or "") >= iso_30d)
    ticket_medio_cents = int(receita_total / transacoes_total) if transacoes_total else 0

    # ── 3. Receita de assinatura (mensalidades cobradas) ──────────
    # Estima pelo nº de usuários PRO ativos × preço mensal.
    try:
        from services.subscription import PRO_PRICE_CENTS
    except Exception:
        PRO_PRICE_CENTS = 4990
    receita_assinatura_mensal = pro_ativos * PRO_PRICE_CENTS

    # ── 4. Ofertas (catálogo: padrao/exclusividade) ────────────────
    ofertas_catalogo = []
    try:
        ofertas_catalogo = (sb.table("ofertas")
                              .select("id, status, valor_cents, tipo, created_at")
                              .order("created_at", desc=True)
                              .limit(2000)
                              .execute()).data or []
    except Exception:
        pass

    of_pendentes = sum(1 for o in ofertas_catalogo if o.get("status") == "pendente")
    # "paga" é o estado final após pagamento Stripe confirmado — conta como aceita/concluída
    of_aceitas   = sum(1 for o in ofertas_catalogo if o.get("status") in ("aceita", "paga", "contra_proposta"))
    of_pagas     = sum(1 for o in ofertas_catalogo if o.get("status") == "paga")
    of_recusadas = sum(1 for o in ofertas_catalogo if o.get("status") == "recusada")
    of_canceladas = sum(1 for o in ofertas_catalogo
                        if o.get("status") in ("cancelada", "expirada"))
    of_total_negociado = sum(int(o.get("valor_cents") or 0)
                             for o in ofertas_catalogo if o.get("status") in ("aceita", "paga"))
    of_ticket_medio = (int(of_total_negociado / max(of_pagas, of_aceitas))
                       if (of_pagas or of_aceitas) else 0)
    taxa_aceite = (round((of_aceitas) / (of_aceitas + of_recusadas) * 100, 1)
                   if (of_aceitas + of_recusadas) > 0 else 0)
    of_exclusividade = sum(1 for o in ofertas_catalogo
                           if (o.get("tipo") or "").lower() == "exclusividade")

    # ── 5. Ofertas de licenciamento (editoras terceiras) ──────────
    ofertas_lic = []
    try:
        ofertas_lic = (sb.table("ofertas_licenciamento")
                         .select("id, status, valor_cents, created_at")
                         .order("created_at", desc=True)
                         .limit(2000)
                         .execute()).data or []
    except Exception:
        pass

    lic_total          = len(ofertas_lic)
    lic_em_andamento   = sum(1 for o in ofertas_lic
                             if o.get("status") in (
                                 "aguardando_pagamento",
                                 "aguardando_editora",
                                 "editora_cadastrada",
                                 "em_assinatura",
                             ))
    lic_concluidas     = sum(1 for o in ofertas_lic
                             if o.get("status") in (
                                 "concluida", "concluído", "confirmada",
                             ))

    # ── 6. Saques pagos (saídas reais para os artistas) ────────────
    total_pago_artistas = 0
    try:
        saques_pagos = (sb.table("saques")
                          .select("valor_cents")
                          .eq("status", "pago")
                          .execute()).data or []
        total_pago_artistas = sum(int(s.get("valor_cents") or 0)
                                  for s in saques_pagos)
    except Exception:
        pass

    # ── 7. Obras: status detalhado ─────────────────────────────────
    obras_por_status = {}
    try:
        obras_rows = (sb.table("obras").select("status").execute()).data or []
        for o in obras_rows:
            st = o.get("status") or "rascunho"
            obras_por_status[st] = obras_por_status.get(st, 0) + 1
    except Exception:
        pass

    return jsonify({
        "atualizado_em": agora.isoformat(),
        "usuarios": {
            "total":           len(perfis),
            "por_papel":       por_role,   # ex: {"compositor": 12, "interprete": 4, "publisher": 2, "administrador": 1}
            "novos_7d":        novos_7d,
            "novos_30d":       novos_30d,
            "pro_ativos":      pro_ativos,
            "pro_past_due":    pro_past_due,
            "starter":         starter_total,
        },
        "receita": {
            "total_cents":            receita_total,
            "ultimos_7d_cents":       receita_7d,
            "ultimos_30d_cents":      receita_30d,
            "plataforma_total_cents": plataforma_total,
            "ticket_medio_cents":     ticket_medio_cents,
            "transacoes_total":       transacoes_total,
            "transacoes_30d":         transacoes_30d,
            "pago_artistas_cents":    total_pago_artistas,
        },
        "assinatura": {
            "preco_pro_cents":        PRO_PRICE_CENTS,
            "pro_ativos":             pro_ativos,
            "receita_mensal_cents":   receita_assinatura_mensal,
            "economia_total_cents":   economia_assinatura_total,
            "economia_30d_cents":     economia_30d,
            "fee_starter_pct":        25,
            "fee_pro_pct":            20,
        },
        "ofertas": {
            "total":               len(ofertas_catalogo),
            "pendentes":           of_pendentes,
            "aceitas":             of_aceitas,
            "pagas":               of_pagas,
            "recusadas":           of_recusadas,
            "canceladas":          of_canceladas,
            "exclusividade":       of_exclusividade,
            "total_negociado_cents": of_total_negociado,
            "ticket_medio_cents":  of_ticket_medio,
            "taxa_aceite_pct":     taxa_aceite,
        },
        "licenciamento_terceiros": {
            "total":         lic_total,
            "em_andamento":  lic_em_andamento,
            "concluidas":    lic_concluidas,
        },
        "obras": {
            "por_status": obras_por_status,
        },
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

@admin_bp.route("/historico-vendas", methods=["GET"])
@require_auth
def historico_vendas_admin():
    """
    Histórico completo de vendas (todas as transações de todos os usuários).

    Query params:
      - status: filtra por status da transação (default: confirmada).
               Use "todas" para não filtrar.
      - dias:  janela em dias a partir de hoje (default: 90, máx: 730)
      - limit: máximo de registros (default: 200, máx: 500)

    Cada item:
      - id, data, status, metodo
      - valor_total_cents, plataforma_cents, liquido_cents
      - obra { id, nome }
      - titular { id, nome }
      - comprador { id, nome }
      - beneficiarios: lista de pagamentos relacionados
        [{ perfil_id, nome, role, valor_cents, share_pct }]
    """
    _check_admin()
    sb = get_supabase()

    from datetime import datetime, timedelta, timezone
    status = request.args.get("status", "confirmada")
    dias   = min(max(int(request.args.get("dias", 90)), 1), 730)
    limit  = min(max(int(request.args.get("limit", 200)), 1), 500)
    desde  = (datetime.now(timezone.utc) - timedelta(days=dias)).isoformat()

    q = (sb.table("transacoes")
           .select("id, created_at, confirmed_at, status, metodo, valor_cents, "
                   "plataforma_cents, liquido_cents, obra_id, comprador_id, "
                   "obras(id, nome, titular_id), "
                   "comprador:perfis!comprador_id(id, nome, nome_completo, nome_artistico)")
           .gte("created_at", desde)
           .order("created_at", desc=True)
           .limit(limit))
    if status and status != "todas":
        q = q.eq("status", status)

    try:
        transacoes = q.execute().data or []
    except Exception:
        # fallback sem joins
        base = (sb.table("transacoes")
                  .select("id, created_at, confirmed_at, status, metodo, valor_cents, "
                          "plataforma_cents, liquido_cents, obra_id, comprador_id")
                  .gte("created_at", desde)
                  .order("created_at", desc=True)
                  .limit(limit))
        if status and status != "todas":
            base = base.eq("status", status)
        transacoes = base.execute().data or []

    if not transacoes:
        return jsonify({
            "itens": [],
            "total_cents": 0,
            "total_transacoes": 0,
            "plataforma_cents": 0,
        }), 200

    tx_ids = [t["id"] for t in transacoes]

    # Resolve titulares faltantes
    titular_ids = {(t.get("obras") or {}).get("titular_id")
                   for t in transacoes if (t.get("obras") or {}).get("titular_id")}
    titular_map = {}
    if titular_ids:
        try:
            tit = (sb.table("perfis")
                     .select("id, nome, nome_completo, nome_artistico, role")
                     .in_("id", list(titular_ids)).execute()).data or []
            titular_map = {p["id"]: p for p in tit}
        except Exception:
            pass

    # Pagamentos relacionados (beneficiários por transação)
    pag_por_tx = {}
    perfil_ids_pag = set()
    try:
        pag_rows = (sb.table("pagamentos_compositores")
                      .select("transacao_id, perfil_id, valor_cents, share_pct")
                      .in_("transacao_id", tx_ids)
                      .execute()).data or []
        for p in pag_rows:
            tid = p.get("transacao_id")
            pag_por_tx.setdefault(tid, []).append(p)
            if p.get("perfil_id"):
                perfil_ids_pag.add(p["perfil_id"])
    except Exception:
        pag_rows = []

    perfis_map = dict(titular_map)
    faltantes = perfil_ids_pag - set(perfis_map.keys())
    if faltantes:
        try:
            extras = (sb.table("perfis")
                        .select("id, nome, nome_completo, nome_artistico, role")
                        .in_("id", list(faltantes)).execute()).data or []
            for p in extras:
                perfis_map[p["id"]] = p
        except Exception:
            pass

    def nome_de(p):
        return (p or {}).get("nome_artistico") or (p or {}).get("nome_completo") or (p or {}).get("nome")

    itens = []
    total_cents = 0
    plataforma_cents = 0
    for t in transacoes:
        obra = t.get("obras") or {}
        comprador = t.get("comprador") or {}
        titular = titular_map.get(obra.get("titular_id")) or {}
        beneficiarios = []
        for p in pag_por_tx.get(t["id"], []):
            perfil = perfis_map.get(p.get("perfil_id")) or {}
            beneficiarios.append({
                "perfil_id":   p.get("perfil_id"),
                "nome":        nome_de(perfil) or "—",
                "role":        perfil.get("role"),
                "valor_cents": int(p.get("valor_cents") or 0),
                "share_pct":   p.get("share_pct"),
            })
        valor = int(t.get("valor_cents") or 0)
        plat  = int(t.get("plataforma_cents") or 0)
        if t.get("status") == "confirmada":
            total_cents += valor
            plataforma_cents += plat
        itens.append({
            "id":                t["id"],
            "data":              t.get("confirmed_at") or t.get("created_at"),
            "status":            t.get("status"),
            "metodo":            t.get("metodo"),
            "valor_total_cents": valor,
            "plataforma_cents":  plat,
            "liquido_cents":     int(t.get("liquido_cents") or 0),
            "obra": {
                "id":   obra.get("id") or t.get("obra_id"),
                "nome": obra.get("nome"),
            },
            "titular": {
                "id":   titular.get("id"),
                "nome": nome_de(titular),
            },
            "comprador": {
                "id":   comprador.get("id") or t.get("comprador_id"),
                "nome": nome_de(comprador),
            },
            "beneficiarios": beneficiarios,
        })

    return jsonify({
        "itens": itens,
        "total_cents": total_cents,
        "plataforma_cents": plataforma_cents,
        "total_transacoes": sum(1 for t in transacoes if t.get("status") == "confirmada"),
        "filtro": {"status": status, "dias": dias, "limit": limit},
    }), 200


@admin_bp.route("/contratos-edicao/reconciliar", methods=["POST"])
@require_auth
def reconciliar_contratos_edicao():
    """
    Varre todas as obras com publisher_id setado e gera contratos de edição
    para as que ainda não têm. Útil quando algum cadastro falhou silenciosamente
    (por exemplo, durante uma indisponibilidade do Supabase).

    Body opcional: { "notificar": true }  (default true) — se enviado false,
    NÃO dispara notificação para as editoras.
    """
    _check_admin()
    data = request.get_json(silent=True) or {}
    notificar = bool(data.get("notificar", True))
    from services.reconciliar_contratos import reconciliar
    resultado = reconciliar(notificar=notificar)
    return jsonify(resultado), 200


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
    """
    Atualiza o status de um saque manualmente pelo admin.

    SEGURANÇA:
    - Nunca dispara Transfers Stripe (esse papel é exclusivo do cron liberar_pendentes).
    - 'pago': apenas para saques em 'processando' (cron já enviou o Transfer).
    - 'rejeitado' de saque em 'processando': wallet JÁ foi debitada → reconstitui antes.
    - 'rejeitado' de saque em 'aguardando_liberacao': wallet ainda não debitada → só cancela.
    - UPDATE condicional com WHERE status=<status_atual> evita race com o cron.
    """
    _check_admin()
    import logging as _lg
    _admin_log = _lg.getLogger("gravan.admin")

    data   = request.get_json(force=True, silent=True) or {}
    acao   = data.get("acao")   # pago | rejeitado
    motivo = (data.get("motivo") or "")[:300]

    if acao not in ("pago", "rejeitado"):
        abort(422, description="Ação inválida. Use 'pago' ou 'rejeitado'.")

    sb = get_supabase()

    saque_r = sb.table("saques").select(
        "id, status, perfil_id, valor_cents"
    ).eq("id", saque_id).maybe_single().execute()
    saque = saque_r.data if saque_r else None
    if not saque:
        abort(404, description="Saque não encontrado.")

    status_atual = saque.get("status")
    EDITAVEIS    = ("processando", "aguardando_liberacao")

    if status_atual not in EDITAVEIS:
        abort(422, description=(
            f"Saque com status '{status_atual}' não pode ser editado manualmente. "
            f"Apenas saques em {EDITAVEIS} podem ser alterados pelo admin."
        ))

    # 'pago' só faz sentido se o cron já debitou e enviou o Transfer.
    if acao == "pago" and status_atual != "processando":
        abort(422, description=(
            "Só é possível marcar como 'pago' um saque que já está em 'processando' "
            "(ou seja, o cron já criou a Stripe Transfer). Use 'rejeitado' para cancelar."
        ))

    # Se rejeitando um saque em 'processando', a wallet JÁ foi debitada pelo cron.
    # Reconstitui o saldo ANTES de atualizar o status para evitar perda de fundos.
    if acao == "rejeitado" and status_atual == "processando":
        try:
            from services.saque_security import _reconstitui_wallet
            _reconstitui_wallet(
                sb,
                saque["perfil_id"],
                int(saque["valor_cents"]),
                f"Rejeitado pelo admin: {motivo or 'sem motivo'}",
            )
        except Exception as e:
            _admin_log.error(
                "Falha ao reconstituir wallet admin (saque=%s): %s", saque_id, e
            )
            abort(500, description="Erro ao reconstituir wallet. Ação cancelada para evitar perda de fundos.")

    # UPDATE condicional: só afeta o saque se ainda estiver no status esperado.
    # Previne race condition entre dois admins ou entre admin e cron.
    update_data = {"status": acao}
    if acao == "rejeitado":
        update_data["cancelado_motivo"] = motivo or "Rejeitado pelo administrador"

    try:
        upd = sb.table("saques").update(update_data).eq(
            "id", saque_id
        ).eq("status", status_atual).execute()
        if not (upd.data if upd else None):
            abort(409, description=(
                "O saque foi modificado por outro processo antes desta ação. "
                "Recarregue a lista e tente novamente."
            ))
    except Exception as e:
        if hasattr(e, "code") and e.code == 409:
            raise
        abort(500, description=f"Erro ao atualizar saque: {str(e)}")

    _admin_log.info(
        "Admin %s marcou saque %s como '%s' (era '%s'). Motivo: %s",
        "admin", saque_id, acao, status_atual, motivo or "—",
    )
    return jsonify({"ok": True, "acao": acao, "saque_id": saque_id}), 200


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
    if not pubs_data:
        return jsonify([]), 200

    pub_ids = [p["id"] for p in pubs_data]

    # ── 3 queries batch em vez de 3×N queries individuais ──────────
    obras_count: dict = {}
    agreg_count: dict = {}
    contr_count: dict = {}
    try:
        for row in (sb.table("obras").select("publisher_id").in_("publisher_id", pub_ids).execute().data or []):
            pid = row["publisher_id"]
            obras_count[pid] = obras_count.get(pid, 0) + 1
    except Exception:
        pass
    try:
        for row in (sb.table("perfis").select("publisher_id").in_("publisher_id", pub_ids).execute().data or []):
            pid = row["publisher_id"]
            agreg_count[pid] = agreg_count.get(pid, 0) + 1
    except Exception:
        pass
    try:
        for row in (sb.table("contracts_edicao").select("publisher_id").in_("publisher_id", pub_ids).execute().data or []):
            pid = row["publisher_id"]
            contr_count[pid] = contr_count.get(pid, 0) + 1
    except Exception:
        pass

    resumo = [
        {**p,
         "total_obras":     obras_count.get(p["id"], 0),
         "total_agregados": agreg_count.get(p["id"], 0),
         "total_contratos": contr_count.get(p["id"], 0)}
        for p in pubs_data
    ]
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

    # Agregados (compositores ligados à editora)
    agregados = []
    try:
        agregados = sb.table("perfis") \
            .select("id, nome, nome_artistico, email, avatar_url, created_at") \
            .eq("publisher_id", publisher_id) \
            .order("created_at", desc=True).execute().data or []
    except Exception:
        pass
    agregados_ids = [a["id"] for a in agregados]

    # Obras da editora — diretamente vinculadas (publisher_id) + obras dos agregados
    obras = []
    try:
        obras_diretas = sb.table("obras") \
            .select("id, nome, publicada, status, preco_cents, created_at, genero, titular_id") \
            .eq("publisher_id", publisher_id) \
            .order("created_at", desc=True).execute().data or []
    except Exception:
        obras_diretas = []

    obras_agregados = []
    if agregados_ids:
        try:
            obras_agregados = sb.table("obras") \
                .select("id, nome, publicada, status, preco_cents, created_at, genero, titular_id") \
                .in_("titular_id", agregados_ids) \
                .order("created_at", desc=True).execute().data or []
        except Exception:
            pass

    # Merge sem duplicatas
    obras_map = {o["id"]: o for o in obras_diretas}
    for o in obras_agregados:
        obras_map.setdefault(o["id"], o)
    obras = sorted(obras_map.values(), key=lambda o: o.get("created_at") or "", reverse=True)
    obras_ids = [o["id"] for o in obras]

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

    # Transações pagas das obras da editora (faturamento total gerado)
    faturamento_cents = 0
    transacoes = []
    if obras_ids:
        try:
            tx = sb.table("transacoes") \
                .select("id, valor_cents, status, created_at, obra_id") \
                .in_("obra_id", obras_ids) \
                .eq("status", "pago") \
                .order("created_at", desc=True).limit(200).execute().data or []
            transacoes = tx
            faturamento_cents = sum(t.get("valor_cents", 0) for t in tx)
        except Exception:
            pass

    # Ganhos reais da editora — pagamentos creditados à editora nesta plataforma
    ganhos_cents = 0
    try:
        pgtos = sb.table("pagamentos_compositores") \
            .select("valor_cents") \
            .eq("perfil_id", publisher_id).execute().data or []
        ganhos_cents = sum(p.get("valor_cents", 0) for p in pgtos)
    except Exception:
        pass

    # Saldo atual da carteira da editora
    saldo_cents = 0
    try:
        wallet = sb.table("wallets").select("saldo_cents") \
            .eq("perfil_id", publisher_id).maybe_single().execute()
        saldo_cents = (wallet.data or {}).get("saldo_cents", 0) if wallet else 0
    except Exception:
        pass

    return jsonify({
        "perfil":    perfil.data,
        "obras":     obras,
        "agregados": agregados,
        "contratos": contratos,
        "transacoes": transacoes[:50],
        "totais": {
            "obras":               len(obras),
            "obras_publicadas":    len([o for o in obras if o.get("publicada") or o.get("status") == "publicada"]),
            "agregados":           len(agregados),
            "contratos":           len(contratos),
            "contratos_assinados": len(contratos_assinados),
            "contratos_pendentes": len(contratos_pendentes),
            "faturamento_cents":   faturamento_cents,
            "fee_devido_cents":    int(faturamento_cents * 0.05),
            "ganhos_cents":        ganhos_cents,
            "saldo_cents":         saldo_cents,
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
@limiter.limit("30 per hour")
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
@limiter.limit("30 per hour")
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


# ──────────────────────────── CONTRATOS ──────────────────────────────
@admin_bp.route("/contratos", methods=["GET"])
@require_auth
def listar_contratos_admin():
    """
    Devolve TODOS os contratos da plataforma (licenciamento + edição) com
    nomes das partes e da obra, em ordem decrescente de criação. Apenas
    administradores. Usado pelo painel admin → aba "Contratos" para
    auditoria. Aceita filtro opcional ?status=concluido|pendente|...
    """
    _check_admin()
    sb = get_supabase()

    status_fil = (request.args.get("status") or "").strip().lower()

    # ── 1. Licenciamento ────────────────────────────────────────────
    q_lic = (sb.table("contracts")
               .select("id, obra_id, seller_id, buyer_id, valor_cents, status, "
                       "created_at, completed_at, versao, trilateral, "
                       "obras(nome)")
               .order("created_at", desc=True)
               .limit(500))
    if status_fil:
        q_lic = q_lic.eq("status", status_fil)
    licenciamento = q_lic.execute().data or []

    # ── 2. Edição ──────────────────────────────────────────────────
    q_ed = (sb.table("contracts_edicao")
              .select("id, obra_id, autor_id, publisher_id, share_pct, status, "
                      "created_at, completed_at, "
                      "signed_by_publisher_at, signed_by_autor_at, "
                      "obras(nome)")
              .order("created_at", desc=True)
              .limit(500))
    if status_fil:
        q_ed = q_ed.eq("status", status_fil)
    edicao = q_ed.execute().data or []

    # ── 3. Resolve nomes de perfis em lote ─────────────────────────
    perfil_ids = set()
    for c in licenciamento:
        if c.get("seller_id"): perfil_ids.add(c["seller_id"])
        if c.get("buyer_id"):  perfil_ids.add(c["buyer_id"])
    for c in edicao:
        if c.get("autor_id"):     perfil_ids.add(c["autor_id"])
        if c.get("publisher_id"): perfil_ids.add(c["publisher_id"])

    perfil_map = {}
    if perfil_ids:
        try:
            rows = (sb.table("perfis")
                      .select("id, nome, nome_artistico, nome_completo, "
                              "razao_social, nome_fantasia, email, role")
                      .in_("id", list(perfil_ids))
                      .execute()).data or []
            perfil_map = {p["id"]: p for p in rows}
        except Exception:
            perfil_map = {}

    def _nome(pid):
        p = perfil_map.get(pid) or {}
        return (p.get("nome_artistico")
                or p.get("razao_social")
                or p.get("nome_fantasia")
                or p.get("nome_completo")
                or p.get("nome")
                or (p.get("email") or "—"))

    itens = []

    for c in licenciamento:
        itens.append({
            "tipo":            "licenciamento",
            "id":              c["id"],
            "status":          c.get("status"),
            "valor_cents":     c.get("valor_cents"),
            "created_at":      c.get("created_at"),
            "completed_at":    c.get("completed_at"),
            "versao":          c.get("versao"),
            "trilateral":      c.get("trilateral", False),
            "obra_id":         c.get("obra_id"),
            "obra_nome":       (c.get("obras") or {}).get("nome"),
            "vendedor": {
                "id":   c.get("seller_id"),
                "nome": _nome(c.get("seller_id")),
            },
            "comprador": {
                "id":   c.get("buyer_id"),
                "nome": _nome(c.get("buyer_id")),
            },
        })

    for c in edicao:
        itens.append({
            "tipo":          "edicao",
            "id":            c["id"],
            "status":        c.get("status"),
            "share_pct":     c.get("share_pct"),
            "created_at":    c.get("created_at"),
            "completed_at":  c.get("completed_at"),
            "obra_id":       c.get("obra_id"),
            "obra_nome":     (c.get("obras") or {}).get("nome"),
            "autor": {
                "id":      c.get("autor_id"),
                "nome":    _nome(c.get("autor_id")),
                "assinou": bool(c.get("signed_by_autor_at")),
            },
            "editora": {
                "id":      c.get("publisher_id"),
                "nome":    _nome(c.get("publisher_id")),
                "assinou": bool(c.get("signed_by_publisher_at")),
            },
        })

    # Ordena tudo junto pela data de criação mais recente
    itens.sort(key=lambda x: x.get("created_at") or "", reverse=True)

    # Estatísticas para o cabeçalho
    em_vigor = sum(
        1 for x in itens
        if (x["tipo"] == "licenciamento" and x["status"] in ("concluido", "concluído"))
        or (x["tipo"] == "edicao"        and x["status"] == "assinado")
    )
    pendentes = sum(
        1 for x in itens
        if x["status"] in ("pendente", "assinado_parcial", "assinado")
    )

    return jsonify({
        "itens":     itens,
        "total":     len(itens),
        "em_vigor":  em_vigor,
        "pendentes": pendentes,
    }), 200


@admin_bp.route("/test-email", methods=["POST"])
@require_auth
@limiter.limit("5 per hour")
def test_email():
    """
    Dispara um e-mail de teste para validar a configuração SMTP.
    Body JSON: { "to": "destino@exemplo.com" }
    Retorna: configuração SMTP (mascarada) + resultado do envio.
    """
    import os
    from services.email_service import send_email, _smtp_configured, _wrap_html

    data = request.get_json(silent=True) or {}
    to = (data.get("to") or "").strip()
    if not to:
        return jsonify({"ok": False, "erro": "Campo 'to' é obrigatório."}), 400

    smtp_host = os.environ.get("SMTP_HOST", "")
    smtp_port = os.environ.get("SMTP_PORT", "587")
    smtp_from = os.environ.get("SMTP_FROM", "")
    smtp_user = os.environ.get("SMTP_USER", "")
    smtp_pass = os.environ.get("SMTP_PASS", "")
    smtp_ssl  = os.environ.get("SMTP_USE_SSL", "")

    def _mask(v):
        if not v:
            return "(não configurado)"
        if len(v) <= 6:
            return "***"
        return v[:3] + "***" + v[-3:]

    configuracao = {
        "SMTP_HOST":    smtp_host or "(não configurado)",
        "SMTP_PORT":    smtp_port,
        "SMTP_FROM":    smtp_from or "(não configurado)",
        "SMTP_USER":    _mask(smtp_user),
        "SMTP_PASS":    _mask(smtp_pass),
        "SMTP_USE_SSL": smtp_ssl or "0",
        "configurado":  _smtp_configured(),
    }

    html = _wrap_html(
        "Teste de e-mail — Gravan",
        """
<h2 style="margin:0 0 6px;font-size:22px;font-weight:800;color:#09090B;">
  Teste de e-mail Gravan
</h2>
<p style="margin:0 0 16px;font-size:14px;color:#52525B;line-height:1.6;">
  Este é um e-mail de teste disparado pelo painel administrativo da Gravan
  para validar a configuração SMTP do servidor de produção.
</p>
<p style="margin:0;font-size:13px;color:#52525B;">
  Se você recebeu esta mensagem, o envio de e-mails automáticos está
  <strong style="color:#16a34a;">funcionando corretamente</strong>.
</p>
        """,
        accent="#16a34a",
    )

    import logging, traceback
    log = logging.getLogger("gravan.admin.test_email")
    ok = False
    erro = None
    try:
        ok = send_email(to=to, subject="[Teste] E-mail automático Gravan", html=html,
                        text="Teste de e-mail Gravan. Se recebeu, o SMTP está funcionando.")
        if not ok:
            erro = "send_email retornou False (SMTP pode estar configurado mas falhou silenciosamente)."
    except Exception as e:
        erro = traceback.format_exc()
        log.error("Falha no test-email: %s", e)

    return jsonify({
        "ok":          ok,
        "simulado":    not _smtp_configured(),
        "enviado_para": to,
        "configuracao": configuracao,
        "erro":        erro,
    }), (200 if ok else 500)
