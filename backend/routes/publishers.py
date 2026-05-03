"""
Rotas para perfil EDITORA (role='publisher').
- POST /api/publishers                    cria perfil de editora a partir de um usuário existente
- GET  /api/publishers/me                 retorna dados da editora logada
- PUT  /api/publishers/me                 atualiza dados da editora
- GET  /api/publishers/dashboard          agregado: obras, contratos, faturamento
- GET  /api/publishers/lookup-by-email    verifica se um e-mail é editora cadastrada
"""
import io
import logging

from flask import Blueprint, request, jsonify, g, abort, send_file

from middleware.auth import require_auth
from db.supabase_client import get_supabase
from utils.audit import log_event
from utils.crypto import encrypt_pii, decrypt_pii
from app import limiter

logger = logging.getLogger(__name__)

publishers_bp = Blueprint("publishers", __name__, url_prefix="/api/publishers")


# ───────────────────────── LOOKUP POR E-MAIL ─────────────────────────
@publishers_bp.get("/lookup-by-email")
@require_auth
def lookup_by_email():
    """
    Verifica se um e-mail pertence a uma editora já cadastrada na plataforma.
    Usado pelo formulário de cadastro de obra (quando compositor marca
    'obra editada por terceira editora').

    Resposta:
      { found: true,  id, razao_social, nome_fantasia, email }
      { found: false }
    """
    email = (request.args.get("email") or "").strip().lower()
    if not email or "@" not in email:
        abort(422, description="Parâmetro 'email' inválido.")

    sb = get_supabase()
    r = (sb.table("perfis")
           .select("id, email, razao_social, nome_fantasia, role")
           .eq("email", email)
           .eq("role", "publisher")
           .limit(1)
           .execute())

    if not r.data:
        return jsonify({"found": False})

    p = r.data[0]
    return jsonify({
        "found":          True,
        "id":             p["id"],
        "email":          p.get("email"),
        "razao_social":   p.get("razao_social"),
        "nome_fantasia":  p.get("nome_fantasia"),
    })


# ────────────────────────── CRIAR EDITORA ────────────────────────────
@publishers_bp.post("")
@publishers_bp.post("/")
@require_auth
@limiter.limit("3 per hour")
def criar_publisher():
    """Promove o usuário logado a EDITORA. Espera os campos PJ no body."""
    # Editora é PJ: não exigimos dados pessoais (nome/CPF do responsável)
    # no cadastro inicial. Esses dados serão coletados quando a editora
    # cadastrar ou convidar um artista.
    REQUIRED_PJ = [
        "razao_social", "nome_fantasia", "cnpj",
        "telefone",
        "endereco_rua", "endereco_numero", "endereco_bairro",
        "endereco_cidade", "endereco_uf", "endereco_cep",
    ]
    data = request.get_json(silent=True) or {}
    faltam = [c for c in REQUIRED_PJ if not data.get(c)]
    if faltam:
        abort(400, description=f"Campos obrigatórios faltando: {', '.join(faltam)}")

    sb = get_supabase()
    payload = {
        "role":              "publisher",
        "razao_social":      data["razao_social"].strip(),
        "nome_fantasia":     data["nome_fantasia"].strip(),
        "cnpj":              encrypt_pii(data["cnpj"].strip()),
        "telefone":          data["telefone"].strip(),
        "endereco_rua":      data["endereco_rua"].strip(),
        "endereco_numero":   data["endereco_numero"].strip(),
        "endereco_bairro":   data["endereco_bairro"].strip(),
        "endereco_cidade":   data["endereco_cidade"].strip(),
        "endereco_uf":       data["endereco_uf"].strip().upper()[:2],
        "endereco_cep":      data["endereco_cep"].strip(),
        "endereco_compl":    (data.get("endereco_compl") or "").strip(),
    }
    # Campos opcionais (mantidos para compat / preenchimento posterior)
    if (data.get("responsavel_nome") or "").strip():
        payload["responsavel_nome"] = data["responsavel_nome"].strip()
    if (data.get("responsavel_cpf") or "").strip():
        payload["responsavel_cpf"] = encrypt_pii(data["responsavel_cpf"].strip())
    r = sb.table("perfis").update(payload).eq("id", g.user.id).execute()
    if not r.data:
        abort(404, description="Perfil não encontrado.")

    log_event("usuario.editado", entity_type="perfil", entity_id=g.user.id,
              metadata={"acao": "promovido_a_publisher",
                        "razao_social": payload["razao_social"]})

    out = dict(r.data[0])
    if out.get("cnpj"):
        try: out["cnpj"] = decrypt_pii(out["cnpj"]) or out["cnpj"]
        except Exception: pass
    if out.get("responsavel_cpf"):
        try: out["responsavel_cpf"] = decrypt_pii(out["responsavel_cpf"]) or out["responsavel_cpf"]
        except Exception: pass
    return jsonify(out)


# ─────────────────────────── ME (GET/PUT) ────────────────────────────
@publishers_bp.get("/me")
@require_auth
def obter_me():
    sb = get_supabase()
    r = sb.table("perfis").select("*").eq("id", g.user.id).single().execute()
    if not r.data or r.data.get("role") != "publisher":
        abort(403, description="Apenas editoras.")
    out = dict(r.data)
    if out.get("cnpj"):
        try: out["cnpj"] = decrypt_pii(out["cnpj"]) or out["cnpj"]
        except Exception: pass
    if out.get("responsavel_cpf"):
        try: out["responsavel_cpf"] = decrypt_pii(out["responsavel_cpf"]) or out["responsavel_cpf"]
        except Exception: pass
    return jsonify(out)


@publishers_bp.put("/me")
@require_auth
@limiter.limit("20 per hour")
def atualizar_me():
    data = request.get_json(silent=True) or {}
    sb = get_supabase()

    me = sb.table("perfis").select("role").eq("id", g.user.id).single().execute()
    if not me.data or me.data.get("role") != "publisher":
        abort(403, description="Apenas editoras.")

    permitidos = {
        "razao_social", "nome_fantasia", "telefone",
        "responsavel_nome", "endereco_rua", "endereco_numero",
        "endereco_compl", "endereco_bairro", "endereco_cidade",
        "endereco_uf", "endereco_cep",
    }
    payload = {k: v for k, v in data.items() if k in permitidos and v is not None}
    if data.get("cnpj"):
        payload["cnpj"] = encrypt_pii(data["cnpj"].strip())
    if data.get("responsavel_cpf"):
        payload["responsavel_cpf"] = encrypt_pii(data["responsavel_cpf"].strip())

    if not payload:
        abort(400, description="Nada para atualizar.")

    r = sb.table("perfis").update(payload).eq("id", g.user.id).execute()
    log_event("usuario.editado", entity_type="perfil", entity_id=g.user.id,
              metadata={"campos": list(payload.keys())})
    return jsonify(r.data[0])


# ─────────────────────────── DASHBOARD ───────────────────────────────
@publishers_bp.get("/dashboard")
@require_auth
def dashboard():
    sb = get_supabase()
    me = sb.table("perfis").select("role").eq("id", g.user.id).single().execute()
    if not me.data or me.data.get("role") != "publisher":
        abort(403, description="Apenas editoras.")

    # Obras vinculadas à editora — agregados (publisher_id) OU editora terceira
    obras = (sb.table("obras")
               .select("id,nome,status,created_at,publisher_id,editora_terceira_id")
               .or_(f"publisher_id.eq.{g.user.id},editora_terceira_id.eq.{g.user.id}")
               .execute())

    agregados = (sb.table("perfis")
                   .select("id,nome_completo,nome_artistico")
                   .eq("publisher_id", g.user.id)
                   .execute())

    contratos = (sb.table("contracts_edicao")
                   .select("id,status,created_at")
                   .eq("publisher_id", g.user.id)
                   .execute())
    contratos_data = contratos.data or []
    contratos_assinados = [c for c in contratos_data if c["status"] == "assinado"]
    contratos_pendentes = [c for c in contratos_data
                           if c["status"] in ("pendente", "assinado_parcial")]

    # ── Faturamento ─────────────────────────────────────────────────
    # Fonte canônica: pagamentos_compositores (linha por crédito de wallet).
    # Cobre tanto agregados (publisher_id_override do titular) quanto
    # editora terceira (publisher_id_override da oferta trilateral).
    faturamento_cents = 0
    comissao_cents = 0
    try:
        pagamentos = (sb.table("pagamentos_compositores")
                        .select("transacao_id,valor_cents")
                        .eq("perfil_id", g.user.id)
                        .execute()).data or []
        comissao_cents = sum(p.get("valor_cents", 0) for p in pagamentos)
        tx_ids = list({p["transacao_id"] for p in pagamentos if p.get("transacao_id")})
        if tx_ids:
            tx = (sb.table("transacoes")
                    .select("valor_cents,status")
                    .in_("id", tx_ids)
                    .in_("status", ["confirmada", "pago"])
                    .execute()).data or []
            faturamento_cents = sum(t.get("valor_cents", 0) for t in tx)
    except Exception:
        pass

    return jsonify({
        "total_obras":          len(obras.data or []),
        "obras_publicadas":     len([o for o in (obras.data or [])
                                     if o.get("status") == "publicada"]),
        "total_agregados":      len(agregados.data or []),
        "contratos_assinados":  len(contratos_assinados),
        "contratos_pendentes":  len(contratos_pendentes),
        "faturamento_cents":    faturamento_cents,
        "comissao_cents":       comissao_cents,
    })


# ──────────────────── HISTÓRICO DE LICENCIAMENTOS ────────────────────
@publishers_bp.get("/historico-licenciamentos")
@require_auth
def historico_licenciamentos():
    """
    Retorna o histórico de licenciamentos em que a editora logada recebeu
    comissão (10% sobre obras de seus agregados), em ordem decrescente.

    Cada item:
      - data, obra (id, nome), titular (id, nome), comprador (id, nome),
        valor_total_cents (transação), comissao_cents (recebido pela editora),
        share_pct
    """
    sb = get_supabase()
    me = sb.table("perfis").select("role").eq("id", g.user.id).single().execute()
    if not me.data or me.data.get("role") != "publisher":
        abort(403, description="Apenas editoras.")

    # Pagamentos creditados à editora
    pagamentos = (sb.table("pagamentos_compositores")
                    .select("id, transacao_id, valor_cents, share_pct, created_at")
                    .eq("perfil_id", g.user.id)
                    .order("created_at", desc=True)
                    .limit(200)
                    .execute()).data or []

    logger.debug("historico-licenciamentos: %d pagamentos encontrados para %s", len(pagamentos), g.user.id)

    if not pagamentos:
        return jsonify({"itens": [], "total_cents": 0, "total_transacoes": 0})

    tx_ids = list({p["transacao_id"] for p in pagamentos if p.get("transacao_id")})
    logger.debug("historico-licenciamentos: tx_ids=%s", tx_ids)

    # Carrega transações — join com obras via obra_id
    tx_map = {}
    obra_map = {}  # obra_id -> {id, nome, titular_id}
    if tx_ids:
        try:
            tx = (sb.table("transacoes")
                    .select("id, valor_cents, status, created_at, obra_id, comprador_id, "
                            "obras(id, nome, titular_id)")
                    .in_("id", tx_ids).execute()).data or []
            logger.debug("historico-licenciamentos: tx com join=%d rows, sample=%s", len(tx), tx[:1])
            tx_map = {t["id"]: t for t in tx}
            # extrair obras do join para facilitar lookup
            for t in tx:
                ob = t.get("obras")
                if isinstance(ob, dict) and ob.get("id"):
                    obra_map[ob["id"]] = ob
                elif isinstance(ob, list) and ob:
                    obra_map[ob[0]["id"]] = ob[0]
        except Exception as e:
            logger.warning("historico-licenciamentos: join obras falhou (%s), tentando sem join", e)
            try:
                tx = (sb.table("transacoes")
                        .select("id, valor_cents, status, created_at, obra_id, comprador_id")
                        .in_("id", tx_ids).execute()).data or []
                tx_map = {t["id"]: t for t in tx}
            except Exception as e2:
                logger.error("historico-licenciamentos: fallback transacoes falhou: %s", e2)
                tx_map = {}

    # Se o join falhou (sem obras no tx_map), buscar obras separadamente por obra_id
    obra_ids_sem_join = [t.get("obra_id") for t in tx_map.values()
                         if t.get("obra_id") and t.get("obra_id") not in obra_map]
    if obra_ids_sem_join:
        try:
            obs = (sb.table("obras")
                     .select("id, nome, titular_id")
                     .in_("id", obra_ids_sem_join).execute()).data or []
            logger.debug("historico-licenciamentos: obras fetch separado=%d", len(obs))
            for ob in obs:
                obra_map[ob["id"]] = ob
        except Exception as e:
            logger.warning("historico-licenciamentos: fetch obras separado falhou: %s", e)

    # Coleta perfil_ids (titular + comprador) para resolver nomes em batch
    perfil_ids = set()
    for t in tx_map.values():
        oid = t.get("obra_id")
        ob = obra_map.get(oid) or {}
        if ob.get("titular_id"):
            perfil_ids.add(ob["titular_id"])
        if t.get("comprador_id"):
            perfil_ids.add(t["comprador_id"])

    logger.debug("historico-licenciamentos: perfil_ids a resolver=%s", perfil_ids)

    perfil_map = {}
    if perfil_ids:
        try:
            prfs = (sb.table("perfis")
                      .select("id, nome_completo, nome_artistico")
                      .in_("id", list(perfil_ids)).execute()).data or []
            logger.debug("historico-licenciamentos: perfis resolvidos=%d", len(prfs))
            perfil_map = {p["id"]: p for p in prfs}
        except Exception as e:
            logger.warning("historico-licenciamentos: fetch perfis falhou: %s", e)

    def _nome(perfil_id):
        p = perfil_map.get(perfil_id) or {}
        return p.get("nome_artistico") or p.get("nome_completo")

    itens = []
    total_cents = 0
    for p in pagamentos:
        t = tx_map.get(p.get("transacao_id")) or {}
        oid = t.get("obra_id")
        obra = obra_map.get(oid) or {}
        titular_id   = obra.get("titular_id")
        comprador_id = t.get("comprador_id")
        itens.append({
            "id":                p["id"],
            "data":              p.get("created_at"),
            "transacao_id":      p.get("transacao_id"),
            "valor_total_cents": t.get("valor_cents"),
            "comissao_cents":    p.get("valor_cents", 0),
            "share_pct":         p.get("share_pct"),
            "obra": {
                "id":   obra.get("id"),
                "nome": obra.get("nome"),
            },
            "titular": {
                "id":   titular_id,
                "nome": _nome(titular_id),
            },
            "comprador": {
                "id":   comprador_id,
                "nome": _nome(comprador_id),
            },
        })
        total_cents += p.get("valor_cents", 0)

    return jsonify({
        "itens":            itens,
        "total_cents":      total_cents,
        "total_transacoes": len(tx_ids),
    })


# ══════════════════════════════════════════════════════════════════
# GET /api/publishers/obras-gerenciadas
# ══════════════════════════════════════════════════════════════════
@publishers_bp.get("/obras-gerenciadas")
@require_auth
def obras_gerenciadas():
    """
    Retorna todas as obras que a editora logada gerencia, para fins de
    geração de dossiê. Inclui:
      1. Obras com publisher_id ou editora_terceira_id = editora
      2. Obras com contracts_edicao assinado pela editora
      3. Obras de artistas agregados (publisher_id no perfil)
    """
    sb = get_supabase()
    me = sb.table("perfis").select("role").eq("id", g.user.id).single().execute()
    if not me.data or me.data.get("role") != "publisher":
        abort(403, description="Apenas editoras.")

    pub_id = str(g.user.id)
    obra_ids = set()

    # 1) obras onde publisher_id ou editora_terceira_id é esta editora
    try:
        r = (sb.table("obras")
               .select("id, nome, status, titular_id")
               .or_(f"publisher_id.eq.{pub_id},editora_terceira_id.eq.{pub_id}")
               .execute()).data or []
        for o in r:
            obra_ids.add(o["id"])
    except Exception:
        pass

    # 2) obras via contracts_edicao
    try:
        r2 = (sb.table("contracts_edicao")
                .select("obra_id")
                .eq("publisher_id", pub_id)
                .execute()).data or []
        for row in r2:
            if row.get("obra_id"):
                obra_ids.add(row["obra_id"])
    except Exception:
        pass

    # 3) obras de artistas agregados
    try:
        agregados = (sb.table("perfis")
                       .select("id")
                       .eq("publisher_id", pub_id)
                       .execute()).data or []
        agg_ids = [a["id"] for a in agregados if a.get("id")]
        if agg_ids:
            r3 = (sb.table("obras")
                    .select("id, nome, status, titular_id")
                    .in_("titular_id", agg_ids)
                    .execute()).data or []
            for o in r3:
                obra_ids.add(o["id"])
    except Exception:
        pass

    if not obra_ids:
        return jsonify([])

    # Busca dados completos das obras
    obras = (sb.table("obras")
               .select("id, nome, status, titular_id, created_at")
               .in_("id", list(obra_ids))
               .order("nome")
               .execute()).data or []

    # Verifica quais já têm dossiê gerado
    dossie_map = {}
    try:
        dossies = (sb.table("dossies")
                     .select("obra_id, id, created_at")
                     .in_("obra_id", list(obra_ids))
                     .execute()).data or []
        for d in dossies:
            dossie_map[d["obra_id"]] = d
    except Exception:
        pass

    # Resolve nomes dos titulares
    titular_ids = list({o["titular_id"] for o in obras if o.get("titular_id")})
    titular_map = {}
    if titular_ids:
        try:
            tit = (sb.table("perfis")
                     .select("id, nome_completo, nome_artistico")
                     .in_("id", titular_ids)
                     .execute()).data or []
            titular_map = {p["id"]: (p.get("nome_artistico") or p.get("nome_completo")) for p in tit}
        except Exception:
            pass

    resultado = []
    for o in obras:
        d = dossie_map.get(o["id"])
        resultado.append({
            "id":            o["id"],
            "nome":          o.get("nome"),
            "status":        o.get("status"),
            "titular_nome":  titular_map.get(o.get("titular_id")),
            "dossie": {
                "id":         d["id"],
                "created_at": d["created_at"],
            } if d else None,
        })

    return jsonify(resultado)


# ════════════════════════════════════════════════════════════════════
# BULK UPLOAD DE OBRAS PELA EDITORA
# ════════════════════════════════════════════════════════════════════
@publishers_bp.get("/bulk-upload/template")
@require_auth
def bulk_upload_template():
    """Baixa o template CSV de bulk upload (UTF-8 com BOM)."""
    sb = get_supabase()
    me = sb.table("perfis").select("role").eq("id", g.user.id).single().execute()
    if not me.data or me.data.get("role") != "publisher":
        abort(403, description="Apenas editoras.")

    from services.bulk_obras import gerar_csv_template
    csv_bytes = gerar_csv_template()
    return send_file(
        io.BytesIO(csv_bytes),
        mimetype="text/csv; charset=utf-8",
        as_attachment=True,
        download_name="gravan-bulk-obras-template.csv",
    )


@publishers_bp.post("/bulk-upload")
@require_auth
def bulk_upload():
    """
    Recebe um .zip (multipart, campo 'arquivo') contendo CSV + .mp3s
    e processa cadastrando as obras em nome dos titulares agregados.
    Retorna o relatório com criadas[] e erros[].
    """
    sb = get_supabase()
    me = (sb.table("perfis")
            .select("role, cadastro_completo")
            .eq("id", g.user.id)
            .single()
            .execute()).data
    if not me or me.get("role") != "publisher":
        abort(403, description="Apenas editoras podem usar o upload em massa.")
    if not me.get("cadastro_completo"):
        abort(422, description="Complete o cadastro da editora antes de usar o upload em massa.")

    if "arquivo" not in request.files:
        abort(422, description="Campo 'arquivo' (.zip) é obrigatório.")
    f = request.files["arquivo"]
    nome = (f.filename or "").lower()
    if not nome.endswith(".zip"):
        abort(422, description="Envie um arquivo .zip contendo o CSV e os MP3s.")

    zip_bytes = f.read()

    from services.bulk_obras import processar_zip
    try:
        relatorio = processar_zip(str(g.user.id), zip_bytes)
    except ValueError as ve:
        abort(422, description=str(ve))
    except Exception as e:
        logger.exception("bulk-upload: erro inesperado %s", e)
        abort(500, description="Erro ao processar o upload em massa.")

    try:
        log_event(
            action="publisher.bulk_upload",
            entity_type="publisher",
            entity_id=str(g.user.id),
            metadata={
                "criadas": len(relatorio.get("criadas") or []),
                "erros": len(relatorio.get("erros") or []),
                "total_csv": relatorio.get("total_csv"),
            },
            user_id=str(g.user.id),
        )
    except Exception:
        pass

    return jsonify(relatorio)
