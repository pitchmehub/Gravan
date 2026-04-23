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
    REQUIRED_PJ = [
        "razao_social", "nome_fantasia", "cnpj",
        "telefone", "responsavel_nome", "responsavel_cpf",
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
        "responsavel_nome":  data["responsavel_nome"].strip(),
        "responsavel_cpf":   encrypt_pii(data["responsavel_cpf"].strip()),
        "endereco_rua":      data["endereco_rua"].strip(),
        "endereco_numero":   data["endereco_numero"].strip(),
        "endereco_bairro":   data["endereco_bairro"].strip(),
        "endereco_cidade":   data["endereco_cidade"].strip(),
        "endereco_uf":       data["endereco_uf"].strip().upper()[:2],
        "endereco_cep":      data["endereco_cep"].strip(),
        "endereco_compl":    (data.get("endereco_compl") or "").strip(),
    }
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

    obras = (sb.table("obras")
               .select("id,nome,status,created_at")
               .eq("publisher_id", g.user.id)
               .execute())
    obras_ids = [o["id"] for o in (obras.data or [])]

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

    faturamento_cents = 0
    if obras_ids:
        try:
            tx = (sb.table("transacoes")
                    .select("valor_cents,status")
                    .in_("obra_id", obras_ids)
                    .eq("status", "pago")
                    .execute())
            faturamento_cents = sum(t.get("valor_cents", 0) for t in (tx.data or []))
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
        "fee_devido_cents":     int(faturamento_cents * 0.05),
    })
