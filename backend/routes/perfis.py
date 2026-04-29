"""Routes: /api/perfis

CORREÇÕES DE VULNERABILIDADES:
- #9 (ALTA): Encryption de CPF e RG
- #15 (MÉDIA): Validação robusta de email
- #14 (MÉDIA): Audit logging
"""
import re
from flask import Blueprint, jsonify, g, abort, request
from middleware.auth import require_auth
from db.supabase_client import get_supabase
from utils.validators import validate_email, validate_cpf
from utils.crypto import encrypt_pii, decrypt_pii
from utils.audit import AuditLogger
from app import limiter

perfis_bp = Blueprint("perfis", __name__)


@perfis_bp.route("/me", methods=["GET"])
@require_auth
def meu_perfil():
    sb = get_supabase()
    resp = sb.table("perfis").select("*, wallets(saldo_cents)").eq("id", g.user.id).single().execute()
    if not resp.data:
        abort(404, description="Perfil não encontrado.")
    return jsonify(resp.data), 200


@perfis_bp.route("/me/completar", methods=["POST"])
@require_auth
@limiter.limit("5 per hour")
def completar_cadastro():
    """
    Completa dados obrigatórios do cadastro: nome completo, CPF, RG, endereço.
    
    CORREÇÃO VULNERABILIDADE #9 (ALTA): CPF e RG são encriptados antes de salvar.
    """
    data = request.get_json(force=True, silent=True) or {}

    nome_completo = (data.get("nome_completo") or "").strip()
    cpf_raw       = (data.get("cpf") or "").strip()
    cpf           = re.sub(r"\D", "", cpf_raw)
    rg            = (data.get("rg") or "").strip()
    endereco_cep  = re.sub(r"\D", "", data.get("endereco_cep") or "")

    if not nome_completo or len(nome_completo) < 5:
        abort(422, description="Nome completo inválido.")
    
    # CORREÇÃO #15: Validação robusta de CPF
    if not validate_cpf(cpf):
        abort(422, description="CPF inválido.")
    
    # Validação de RG: 5–14 caracteres, apenas dígitos (X aceito como dígito verificador final)
    rg_limpo = re.sub(r"[^0-9Xx]", "", rg)
    if len(rg_limpo) < 5 or len(rg_limpo) > 14:
        abort(422, description="RG inválido (informe 5 a 14 dígitos).")
    nucleo = rg_limpo[:-1] if rg_limpo[-1] in ("X", "x") else rg_limpo
    if not nucleo.isdigit():
        abort(422, description="RG inválido (apenas dígitos, com X opcional ao final).")
    rg = rg_limpo.upper()

    # CORREÇÃO VULNERABILIDADE #9 (ALTA): Encrypt PII antes de salvar
    cpf_encrypted = encrypt_pii(cpf)
    rg_encrypted = encrypt_pii(rg)
    
    fields = {
        "nome_completo":   nome_completo,
        "cpf":             cpf_encrypted,  # ENCRYPTED
        "rg":              rg_encrypted,   # ENCRYPTED
        "endereco_rua":    (data.get("endereco_rua")    or "").strip(),
        "endereco_numero": (data.get("endereco_numero") or "").strip(),
        "endereco_compl":  (data.get("endereco_compl")  or "").strip() or None,
        "endereco_bairro": (data.get("endereco_bairro") or "").strip(),
        "endereco_cidade": (data.get("endereco_cidade") or "").strip(),
        "endereco_uf":     (data.get("endereco_uf")     or "").strip().upper()[:2],
        "endereco_cep":    endereco_cep or None,
        "cadastro_completo": True,
    }

    # Valida endereço mínimo
    for campo in ("endereco_rua", "endereco_numero", "endereco_bairro", "endereco_cidade", "endereco_uf"):
        if not fields[campo]:
            abort(422, description=f"Campo de endereço obrigatório: {campo.replace('endereco_', '')}")
    if not endereco_cep or len(endereco_cep) != 8:
        abort(422, description="CEP inválido (8 dígitos).")

    sb = get_supabase()

    # Verifica se CPF já está em uso (compara encrypted)
    # NOTA: Em produção ideal, usar hash para busca de duplicata
    existente = sb.table("perfis").select("id, cpf").neq("id", g.user.id).execute()
    for perfil in (existente.data or []):
        if decrypt_pii(perfil.get("cpf", "")) == cpf:
            abort(409, description="Este CPF já está cadastrado em outra conta.")

    sb.table("perfis").update(fields).eq("id", g.user.id).execute()
    return jsonify({"ok": True, "cadastro_completo": True}), 200


@perfis_bp.route("/me/wallet", methods=["GET"])
@require_auth
def minha_wallet():
    sb = get_supabase()
    try:
        wallet = sb.table("wallets").select("saldo_cents").eq(
            "perfil_id", g.user.id
        ).maybe_single().execute()
        saldo = ((wallet.data if wallet else None) or {}).get("saldo_cents") or 0
    except Exception:
        saldo = 0

    try:
        saques = sb.table("saques").select("*").eq(
            "perfil_id", g.user.id
        ).order("created_at", desc=True).limit(20).execute()
        lista = saques.data or []
    except Exception:
        lista = []

    return jsonify({
        "saldo_cents": saldo,
        "saques":      lista,
    }), 200


@perfis_bp.route("/me/saques", methods=["POST"])
@require_auth
def solicitar_saque():
    from flask import abort
    abort(410, description=(
        "Endpoint descontinuado. Use POST /api/saques/iniciar "
        "(novo fluxo com OTP por e-mail e janela de 24h)."
    ))


@perfis_bp.route("/me/compras", methods=["GET"])
@require_auth
def minhas_compras():
    sb = get_supabase()
    resp = (
        sb.table("transacoes")
        .select("id, created_at, confirmed_at, status, metodo, valor_cents, obras(id, nome, audio_path, genero, perfis!titular_id(nome, nome_artistico))")
        .eq("comprador_id", g.user.id)
        .order("created_at", desc=True)
        .limit(50)
        .execute()
    )
    compras = []
    for t in (resp.data or []):
        obra = t.get("obras") or {}
        compras.append({
            "id":           t["id"],
            "created_at":   t["created_at"],
            "confirmed_at": t.get("confirmed_at"),
            "status":       t["status"],
            "metodo":       t["metodo"],
            "valor_cents":  t["valor_cents"],
            "obra_id":      obra.get("id"),
            "obra_nome":    obra.get("nome"),
            "audio_path":   obra.get("audio_path"),
            "genero":       obra.get("genero"),
            "titular_nome": (obra.get("perfis") or {}).get("nome_artistico") or (obra.get("perfis") or {}).get("nome"),
        })
    return jsonify(compras), 200


@perfis_bp.route("/me/dashboard", methods=["GET"])
@require_auth
def dashboard_compositor():
    """Estatisticas agregadas do compositor para a dashboard."""
    sb = get_supabase()

    perfil = sb.table("perfis").select(
        "id, nome, plano, status_assinatura"
    ).eq("id", g.user.id).maybe_single().execute()
    p_data = (perfil.data if perfil else None) or {}
    plano_efetivo = p_data.get("plano", "STARTER")
    if plano_efetivo == "PRO" and p_data.get("status_assinatura") not in ("ativa", "cancelada", "past_due"):
        plano_efetivo = "STARTER"

    # Todas as obras em que o usuario eh titular ou coautor
    coaut = sb.table("coautorias").select("obra_id, is_titular, obras(id, nome, status, preco_cents, created_at, genero, audio_path)").eq("perfil_id", g.user.id).execute()
    obras_map = {}
    for c in (coaut.data or []):
        o = c.get("obras")
        if o and o["id"] not in obras_map:
            obras_map[o["id"]] = {**o, "sou_titular": c.get("is_titular", False)}
    obras = list(obras_map.values())

    total_obras      = len(obras)
    obras_publicadas = sum(1 for o in obras if o.get("status") == "publicada")
    obras_rascunho   = sum(1 for o in obras if o.get("status") != "publicada")

    # Vendas e receita
    obra_ids = [o["id"] for o in obras]
    total_vendas = 0
    receita_total = 0
    if obra_ids:
        trans = sb.table("transacoes").select("id, obra_id, valor_cents, status").in_("obra_id", obra_ids).eq("status", "confirmada").execute()
        total_vendas = len(trans.data or [])

        # Receita efetiva (pagamentos recebidos)
        pag = sb.table("pagamentos_compositores").select("valor_cents").eq("perfil_id", g.user.id).execute()
        receita_total = sum((p.get("valor_cents") or 0) for p in (pag.data or []))

    # Saldo atual (cria wallet vazia se não existir)
    try:
        wallet = sb.table("wallets").select("saldo_cents").eq("perfil_id", g.user.id).maybe_single().execute()
        saldo_atual = ((wallet.data if wallet else None) or {}).get("saldo_cents") or 0
    except Exception:
        saldo_atual = 0

    # Total ja sacado
    saques = sb.table("saques").select("valor_cents, status").eq("perfil_id", g.user.id).execute()
    total_sacado = sum(s["valor_cents"] for s in (saques.data or []) if s.get("status") == "pago")

    # Limites de preço por plano (Free vs PRO)
    preco_min = 100
    preco_max = 1000000 if plano_efetivo == "PRO" else 100000

    # Ordena obras por data (mais recente primeiro)
    obras_sorted = sorted(obras, key=lambda x: x.get("created_at") or "", reverse=True)

    return jsonify({
        "plano":            plano_efetivo,
        "preco_min_cents":  preco_min,
        "preco_max_cents":  preco_max,
        "total_obras":      total_obras,
        "obras_publicadas": obras_publicadas,
        "obras_rascunho":   obras_rascunho,
        "total_vendas":     total_vendas,
        "receita_total_cents": receita_total,
        "saldo_atual_cents":   saldo_atual,
        "total_sacado_cents":  total_sacado,
        "obras": obras_sorted,
    }), 200


@perfis_bp.route("/buscar-por-email", methods=["GET"])
@require_auth
@limiter.limit("10 per minute")
def buscar_por_email():
    """
    Busca compositor por email de cadastro (usado para adicionar coautor).
    
    CORREÇÃO #15 (MÉDIA): Validação robusta de email.
    """
    email = (request.args.get("email") or "").strip().lower()
    
    # CORREÇÃO #15: Validação robusta
    if not validate_email(email):
        abort(422, description="Email inválido.")

    sb = get_supabase()
    try:
        resp = sb.table("perfis").select(
            "id, nome, nome_artistico, nome_completo, email, role"
        ).eq("email", email).limit(1).execute()
    except Exception as e:
        abort(500, description=f"Erro na busca: {str(e)}")

    if not resp.data:
        abort(404, description="Nenhum compositor cadastrado com este email.")

    perfil = resp.data[0]
    return jsonify(perfil), 200


@perfis_bp.route("/me/contratos", methods=["GET"])
@require_auth
def meus_contratos():
    """Lista os contratos de edição assinados pelo compositor."""
    sb = get_supabase()
    # Tenta com versao; fallback sem versao caso a coluna não exista
    try:
        resp = sb.table("contratos_edicao").select(
            "id, obra_id, assinado_em, versao, obras(nome)"
        ).eq("titular_id", g.user.id).order("assinado_em", desc=True).execute()
    except Exception:
        resp = sb.table("contratos_edicao").select(
            "id, obra_id, assinado_em, obras(nome)"
        ).eq("titular_id", g.user.id).order("assinado_em", desc=True).execute()
    return jsonify(resp.data or []), 200


@perfis_bp.route("/contratos/<contrato_id>", methods=["GET"])
@require_auth
def detalhe_contrato(contrato_id):
    sb = get_supabase()
    resp = sb.table("contratos_edicao").select("*").eq("id", contrato_id).eq("titular_id", g.user.id).single().execute()
    if not resp.data:
        abort(404, description="Contrato não encontrado.")
    return jsonify(resp.data), 200


@perfis_bp.route("/contratos/<contrato_id>/pdf", methods=["GET"])
@require_auth
@limiter.limit("10 per hour")
def contrato_pdf(contrato_id):
    """Gera o PDF do contrato de edição assinado. Rate limit: 10 downloads/hora/IP."""
    from flask import send_file
    from services.contrato_pdf import gerar_pdf_contrato
    import io
    sb = get_supabase()
    resp = sb.table("contratos_edicao").select("*").eq("id", contrato_id).eq("titular_id", g.user.id).single().execute()
    if not resp.data:
        abort(404, description="Contrato não encontrado.")
    pdf_bytes = gerar_pdf_contrato(resp.data)
    buf = io.BytesIO(pdf_bytes)
    buf.seek(0)
    return send_file(
        buf,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"contrato-edicao-{contrato_id[:8]}.pdf",
    )


# ═══════════════════════════════════════════════════════════════════════
# DEFINIR TIPO DE PERFIL (compositor / interprete / publisher)
# Usado na primeira vez que o usuário entra (especialmente login Google)
# ═══════════════════════════════════════════════════════════════════════
@perfis_bp.route("/me/tipo", methods=["POST"])
@require_auth
@limiter.limit("10 per hour")
def definir_tipo_perfil():
    """
    Define o tipo de perfil (role) na primeira vez que o usuário entra.
    Aceita: 'compositor', 'interprete' ou 'publisher' (editora).
    Só permite definir se o perfil ainda não tem role definida.
    """
    data = request.get_json(force=True, silent=True) or {}
    role = (data.get("role") or "").strip().lower()

    ROLES_VALIDOS = {"compositor", "interprete", "publisher"}
    if role not in ROLES_VALIDOS:
        abort(422, description="Tipo de perfil invalido. Use: compositor, interprete ou publisher.")

    sb = get_supabase()

    atual = sb.table("perfis").select("id, role").eq("id", g.user.id).maybe_single().execute()

    if atual and atual.data:
        role_atual = (atual.data.get("role") or "").strip().lower()
        if role_atual and role_atual != role:
            abort(409, description="Tipo de perfil ja definido. Para alterar, fale com o suporte.")
        sb.table("perfis").update({"role": role}).eq("id", g.user.id).execute()
    else:
        nome = (g.user.user_metadata or {}).get("full_name") or (g.user.email or "").split("@")[0]
        sb.table("perfis").insert({
            "id":    g.user.id,
            "email": g.user.email,
            "nome":  nome,
            "role":  role,
        }).execute()

    AuditLogger.log("perfil.tipo_definido", entity_type="perfil",
                    entity_id=g.user.id, metadata={"role": role})

    return jsonify({"ok": True, "role": role}), 200
