"""
Rotas para perfil EDITORA (role='publisher').
- POST /api/publishers                    cria perfil de editora a partir de um usuário existente
- GET  /api/publishers/me                 retorna dados da editora logada
- PUT  /api/publishers/me                 atualiza dados da editora
- GET  /api/publishers/dashboard          agregado: obras, contratos, faturamento
- GET  /api/publishers/lookup-by-email    verifica se um e-mail é editora cadastrada
"""
from flask import Blueprint, request, jsonify, g, abort

from middleware.auth import require_auth
from db.supabase_client import get_supabase
from utils.audit import log_event
from utils.crypto import encrypt_pii, decrypt_pii

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

    if not pagamentos:
        return jsonify({"itens": [], "total_cents": 0, "total_transacoes": 0})

    tx_ids = list({p["transacao_id"] for p in pagamentos if p.get("transacao_id")})

    # Carrega transações (com obra e comprador)
    tx_map = {}
    if tx_ids:
        try:
            tx = (sb.table("transacoes")
                    .select("id, valor_cents, status, created_at, obra_id, comprador_id, "
                            "obras(id, nome, titular_id), "
                            "comprador:perfis!comprador_id(id, nome_completo, nome_artistico)")
                    .in_("id", tx_ids).execute()).data or []
            tx_map = {t["id"]: t for t in tx}
        except Exception:
            # Fallback simples sem joins
            try:
                tx = (sb.table("transacoes")
                        .select("id, valor_cents, status, created_at, obra_id, comprador_id")
                        .in_("id", tx_ids).execute()).data or []
                tx_map = {t["id"]: t for t in tx}
            except Exception:
                tx_map = {}

    # Coleta titular_ids para resolver nomes
    titular_ids = set()
    for t in tx_map.values():
        obra = t.get("obras") or {}
        if obra.get("titular_id"):
            titular_ids.add(obra["titular_id"])

    titular_map = {}
    if titular_ids:
        try:
            tit = (sb.table("perfis")
                     .select("id, nome_completo, nome_artistico")
                     .in_("id", list(titular_ids)).execute()).data or []
            titular_map = {p["id"]: p for p in tit}
        except Exception:
            pass

    itens = []
    total_cents = 0
    for p in pagamentos:
        t = tx_map.get(p.get("transacao_id")) or {}
        obra = t.get("obras") or {}
        titular = titular_map.get(obra.get("titular_id")) or {}
        comprador = t.get("comprador") or {}
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
                "id":   titular.get("id"),
                "nome": titular.get("nome_artistico") or titular.get("nome_completo"),
            },
            "comprador": {
                "id":   comprador.get("id"),
                "nome": comprador.get("nome_artistico") or comprador.get("nome_completo"),
            },
        })
        total_cents += p.get("valor_cents", 0)

    return jsonify({
        "itens":            itens,
        "total_cents":      total_cents,
        "total_transacoes": len(tx_ids),
    })
