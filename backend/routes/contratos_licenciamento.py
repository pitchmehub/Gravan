"""Routes: /api/contratos/licenciamento — contratos de gravação/exploração."""
import hashlib
import io
import logging
from datetime import datetime
from flask import Blueprint, request, jsonify, g, abort, send_file
from middleware.auth import require_auth
from db.supabase_client import get_supabase
from services.contrato_licenciamento import (
    aceitar_contrato,
    TEMPLATE_LICENCIAMENTO,
    TEMPLATE_TRILATERAL,
    _moeda,
    _endereco,
    _cidade_uf,
    _decrypt,
)
from services.contrato_pdf import gerar_pdf_contrato
from services.dossie_licenca import gerar_zip_dossie_licenca
from utils.crypto import hash_ip
from app import limiter

logger = logging.getLogger(__name__)

contratos_lic_bp = Blueprint("contratos_lic", __name__)


def _user_tem_acesso(sb, contract_id: str, user_id: str) -> dict | None:
    """Retorna o contrato se o usuário é parte; None caso contrário."""
    c = sb.table("contracts").select("*").eq("id", contract_id).single().execute().data
    if not c:
        return None
    if c["seller_id"] == user_id or c["buyer_id"] == user_id:
        return c
    # Coautor?
    s = sb.table("contract_signers").select("id").eq("contract_id", contract_id).eq("user_id", user_id).limit(1).execute().data
    if s:
        return c
    return None


@contratos_lic_bp.route("/templates", methods=["GET"])
def templates():
    """Público — devolve os textos integrais dos templates de contrato
    realmente usados na geração final. Permite que telas de pré-visualização
    (Comprar, Aceitar Oferta, Modal de Edição) exibam o contrato completo
    antes da assinatura."""
    sb = get_supabase()
    edicao = ""
    try:
        r = sb.table("landing_content").select("valor").eq(
            "id", "contrato_edicao_template"
        ).maybe_single().execute()
        edicao = ((r.data if r else None) or {}).get("valor") or ""
    except Exception:
        pass
    return jsonify({
        "licenciamento_bilateral":  TEMPLATE_LICENCIAMENTO,
        "licenciamento_trilateral": TEMPLATE_TRILATERAL,
        "edicao_bilateral":         edicao,
    }), 200


def _build_autores_e_split(sb, obra: dict, titular: dict):
    """Monta autores_bloco, split_lista e nomes artísticos a partir das coautorias."""
    coaut = sb.table("coautorias").select("perfil_id, share_pct").eq("obra_id", obra["id"]).execute().data or []
    if not coaut:
        coaut = [{"perfil_id": titular["id"], "share_pct": 100}]
    ids = list({c["perfil_id"] for c in coaut})
    perfis = sb.table("perfis").select(
        "id, nome, nome_artistico, nome_completo, cpf, rg,"
        " endereco_rua, endereco_numero, endereco_compl, endereco_bairro,"
        " endereco_cidade, endereco_uf, email"
    ).in_("id", ids).execute().data or []
    por_id = {p["id"]: p for p in perfis}
    ordered = sorted(coaut, key=lambda c: 0 if c["perfil_id"] == titular["id"] else 1)

    autores_bloco_partes = []
    split_lista_partes = []
    autores_nomes_artisticos = []
    for c in ordered:
        p = por_id.get(c["perfil_id"], {})
        is_titular = c["perfil_id"] == titular["id"]
        papel = "AUTOR PRINCIPAL" if is_titular else "COAUTOR"
        autores_bloco_partes.append(
            f"[{papel}]\n"
            f"Nome: {p.get('nome_completo') or p.get('nome') or '—'}\n"
            f"CPF: {_decrypt(p.get('cpf', '')) or 'Não informado'}\n"
            f"RG: {_decrypt(p.get('rg', '')) or 'Não informado'}\n"
            f"Endereço: {_endereco(p)}\n"
            f"Cidade/UF: {_cidade_uf(p)}\n"
        )
        split_lista_partes.append(
            f"- {p.get('nome_completo') or p.get('nome') or '—'}: {float(c['share_pct']):.2f}%"
        )
        autores_nomes_artisticos.append(p.get("nome_artistico") or p.get("nome") or "—")
    return (
        "\n".join(autores_bloco_partes).strip(),
        "\n".join(split_lista_partes),
        ", ".join(autores_nomes_artisticos),
    )


@contratos_lic_bp.route("/preview", methods=["GET"])
@require_auth
def preview():
    """Renderiza o texto integral do contrato como será gerado, com os dados
    reais da obra, do(s) autor(es) e do comprador (g.user). Usado pela tela
    de Compra para mostrar o contrato COMPLETO antes de pagar."""
    obra_id = request.args.get("obra_id")
    if not obra_id:
        abort(400, description="obra_id obrigatório.")
    valor_param = request.args.get("valor_cents")
    sb = get_supabase()

    obra = sb.table("obras").select("*").eq("id", obra_id).maybe_single().execute()
    obra = (obra.data if obra else None)
    if not obra:
        abort(404, description="Obra não encontrada.")

    titular = sb.table("perfis").select("*").eq("id", obra["titular_id"]).maybe_single().execute()
    titular = (titular.data if titular else None) or {}

    buyer = sb.table("perfis").select("*").eq("id", g.user.id).maybe_single().execute()
    buyer = (buyer.data if buyer else None) or {}

    valor_cents = int(valor_param) if (valor_param and valor_param.isdigit()) else int(obra.get("preco_cents") or 0)

    autores_bloco, split_lista, nomes_art = _build_autores_e_split(sb, obra, titular)

    # Tipo: trilateral se titular é AGREGADO de uma editora-mãe
    if titular.get("publisher_id"):
        editora = sb.table("perfis").select("*").eq("id", titular["publisher_id"]).maybe_single().execute()
        editora = (editora.data if editora else None) or {}
        cnpj_dec = _decrypt(editora.get("cnpj", "")) or "Não informado"
        editora_endereco = ", ".join(filter(None, [
            editora.get("endereco_rua"), editora.get("endereco_numero"),
            editora.get("endereco_compl"), editora.get("endereco_bairro"),
            editora.get("endereco_cidade"), editora.get("endereco_uf"),
        ])) or "Não informado"
        clausula_split_editora = (
            "\n\nNos termos do contrato de agregação vigente entre AUTOR(ES) e EDITORA, "
            "a GRAVAN, na qualidade de plataforma intermediária, fica autorizada e "
            "obrigada a creditar automaticamente, em cada licenciamento desta obra, "
            "o percentual de 10% (dez por cento) do valor pago pelo LICENCIADO "
            "diretamente à EDITORA, sendo o saldo remanescente, deduzida a taxa de "
            "intermediação da GRAVAN, distribuído ao(s) AUTOR(ES) conforme o split "
            "declarado na Cláusula 7."
        )
        conteudo = (TEMPLATE_TRILATERAL
            .replace("{{autores_bloco}}",          autores_bloco)
            .replace("{{editora_razao}}",          editora.get("razao_social") or editora.get("nome_completo") or editora.get("nome") or "—")
            .replace("{{editora_cnpj}}",           cnpj_dec)
            .replace("{{editora_responsavel}}",    editora.get("responsavel_nome") or editora.get("nome_completo") or editora.get("nome") or "—")
            .replace("{{editora_email}}",          editora.get("email") or "—")
            .replace("{{editora_endereco}}",       editora_endereco)
            .replace("{{interprete_nome}}",        buyer.get("nome_completo") or buyer.get("nome") or "—")
            .replace("{{interprete_nome_artistico}}", buyer.get("nome_artistico") or "Não informado")
            .replace("{{interprete_cpf}}",         _decrypt(buyer.get("cpf","")) or "Não informado")
            .replace("{{interprete_rg}}",          _decrypt(buyer.get("rg","")) or "Não informado")
            .replace("{{interprete_email}}",       buyer.get("email") or "Não informado")
            .replace("{{interprete_endereco}}",    _endereco(buyer))
            .replace("{{interprete_cidade_uf}}",   _cidade_uf(buyer))
            .replace("{{obra_nome}}",              obra.get("nome", "—"))
            .replace("{{obra_letra}}",             (obra.get("letra") or "").strip() or "—")
            .replace("{{valor_buyout_extenso}}",   _moeda(valor_cents))
            .replace("{{split_lista}}",            split_lista)
            .replace("{{clausula_split_editora}}", clausula_split_editora)
            .replace("{{data_emissao}}",           datetime.utcnow().strftime("%d/%m/%Y às %H:%M UTC"))
        )
        tipo = "trilateral"
    else:
        conteudo = (TEMPLATE_LICENCIAMENTO
            .replace("{{autores_bloco}}",            autores_bloco)
            .replace("{{interprete_nome}}",          buyer.get("nome_completo") or buyer.get("nome") or "—")
            .replace("{{interprete_cpf}}",           _decrypt(buyer.get("cpf","")) or "Não informado")
            .replace("{{interprete_endereco}}",      _endereco(buyer))
            .replace("{{interprete_cidade_uf}}",     _cidade_uf(buyer))
            .replace("{{obra_nome}}",                obra.get("nome","—"))
            .replace("{{obra_letra}}",               (obra.get("letra") or "").strip() or "—")
            .replace("{{valor_buyout_extenso}}",     _moeda(valor_cents))
            .replace("{{autores_nomes_artisticos}}", nomes_art)
            .replace("{{isrc}}",                     obra.get("isrc") or "a definir após lançamento")
            .replace("{{iswc}}",                     obra.get("iswc") or "a definir após lançamento")
            .replace("{{split_lista}}",              split_lista)
            .replace("{{data_emissao}}",             datetime.utcnow().strftime("%d/%m/%Y às %H:%M UTC"))
        )
        tipo = "bilateral"

    # Hash provisório do preview (o final será recalculado na geração real)
    h = hashlib.sha256(conteudo.encode("utf-8")).hexdigest()
    conteudo = conteudo.replace("{{conteudo_hash}}", f"{h} (preview — recalculado quando todas as partes assinarem)")
    return jsonify({"tipo": tipo, "conteudo": conteudo, "valor_cents": valor_cents}), 200


@contratos_lic_bp.route("/preview-oferta/<token>", methods=["GET"])
def preview_oferta(token):
    """Pré-visualização do contrato TRILATERAL (autor + editora-terceira + Gravan
    + intérprete) gerado a partir de uma OFERTA com terceira editora. Usado na
    página /editora/aceitar-oferta/<token> antes da editora aceitar."""
    sb = get_supabase()
    of = sb.table("ofertas_licenciamento").select("*").eq("registration_token", token).maybe_single().execute()
    of = (of.data if of else None)
    if not of:
        abort(404, description="Oferta não encontrada ou link expirado.")

    obra = sb.table("obras").select("*").eq("id", of["obra_id"]).maybe_single().execute()
    obra = (obra.data if obra else None)
    if not obra:
        abort(404, description="Obra não encontrada.")
    titular = sb.table("perfis").select("*").eq("id", obra["titular_id"]).maybe_single().execute()
    titular = (titular.data if titular else None) or {}
    buyer = sb.table("perfis").select("*").eq("id", of["comprador_id"]).maybe_single().execute()
    buyer = (buyer.data if buyer else None) or {}

    # Editora terceira: pode já existir no perfil ou ainda estar só na oferta
    editora = {}
    if of.get("editora_terceira_id"):
        e = sb.table("perfis").select("*").eq("id", of["editora_terceira_id"]).maybe_single().execute()
        editora = (e.data if e else None) or {}

    autores_bloco, split_lista, _ = _build_autores_e_split(sb, obra, titular)

    cnpj_dec = _decrypt(editora.get("cnpj", "")) if editora else ""
    editora_endereco = ", ".join(filter(None, [
        editora.get("endereco_rua"), editora.get("endereco_numero"),
        editora.get("endereco_compl"), editora.get("endereco_bairro"),
        editora.get("endereco_cidade"), editora.get("endereco_uf"),
    ])) if editora else ""

    conteudo = (TEMPLATE_TRILATERAL
        .replace("{{autores_bloco}}",          autores_bloco)
        .replace("{{editora_razao}}",          editora.get("razao_social") or of.get("editora_terceira_nome") or "(razão social da sua editora)")
        .replace("{{editora_cnpj}}",           cnpj_dec or "(CNPJ a confirmar no cadastro)")
        .replace("{{editora_responsavel}}",    editora.get("responsavel_nome") or "(responsável legal a confirmar)")
        .replace("{{editora_email}}",          editora.get("email") or of.get("editora_terceira_email") or "(e-mail da editora)")
        .replace("{{editora_endereco}}",       editora_endereco or "(endereço a confirmar no cadastro)")
        .replace("{{interprete_nome}}",        buyer.get("nome_completo") or buyer.get("nome") or "—")
        .replace("{{interprete_nome_artistico}}", buyer.get("nome_artistico") or "Não informado")
        .replace("{{interprete_cpf}}",         _decrypt(buyer.get("cpf","")) or "Não informado")
        .replace("{{interprete_rg}}",          _decrypt(buyer.get("rg","")) or "Não informado")
        .replace("{{interprete_email}}",       buyer.get("email") or "Não informado")
        .replace("{{interprete_endereco}}",    _endereco(buyer))
        .replace("{{interprete_cidade_uf}}",   _cidade_uf(buyer))
        .replace("{{obra_nome}}",              obra.get("nome", "—"))
        .replace("{{obra_letra}}",             (obra.get("letra") or "").strip() or "—")
        .replace("{{valor_buyout_extenso}}",   _moeda(of.get("valor_cents") or 0))
        .replace("{{split_lista}}",            split_lista)
        .replace("{{clausula_split_editora}}", "")
        .replace("{{data_emissao}}",           datetime.utcnow().strftime("%d/%m/%Y às %H:%M UTC"))
    )
    h = hashlib.sha256(conteudo.encode("utf-8")).hexdigest()
    conteudo = conteudo.replace("{{conteudo_hash}}", f"{h} (preview — recalculado quando todas as partes assinarem)")
    return jsonify({"tipo": "trilateral", "conteudo": conteudo}), 200


@contratos_lic_bp.route("", methods=["GET"])
@contratos_lic_bp.route("/", methods=["GET"])
@require_auth
def listar():
    """Lista contratos de licenciamento onde o usuário é parte (autor, coautor ou intérprete)."""
    sb = get_supabase()
    # Pega contratos onde ele é seller, buyer ou signer
    own = sb.table("contracts").select(
        "id, obra_id, seller_id, buyer_id, valor_cents, status, created_at, completed_at, versao, obras(nome)"
    ).or_(f"seller_id.eq.{g.user.id},buyer_id.eq.{g.user.id}").order("created_at", desc=True).execute().data or []

    # Coautor (não seller, não buyer)
    coaut_ids = sb.table("contract_signers").select("contract_id").eq("user_id", g.user.id).execute().data or []
    extra_ids = [r["contract_id"] for r in coaut_ids if r["contract_id"] not in {c["id"] for c in own}]
    if extra_ids:
        extras = sb.table("contracts").select(
            "id, obra_id, seller_id, buyer_id, valor_cents, status, created_at, completed_at, versao, obras(nome)"
        ).in_("id", extra_ids).execute().data or []
        own.extend(extras)

    # Adiciona info do meu papel em cada contrato
    contract_ids = [c["id"] for c in own]
    mine = {}
    if contract_ids:
        rows = sb.table("contract_signers").select("contract_id, role, signed, signed_at").in_("contract_id", contract_ids).eq("user_id", g.user.id).execute().data or []
        for r in rows:
            mine[r["contract_id"]] = r

    for c in own:
        c["meu_papel"] = (mine.get(c["id"]) or {}).get("role")
        c["minha_assinatura"] = bool((mine.get(c["id"]) or {}).get("signed"))

    return jsonify(own), 200


@contratos_lic_bp.route("/<contract_id>", methods=["GET"])
@require_auth
def detalhe(contract_id):
    sb = get_supabase()
    c = _user_tem_acesso(sb, contract_id, g.user.id)
    if not c:
        abort(404, description="Contrato não encontrado.")
    signers = sb.table("contract_signers").select(
        "user_id, role, share_pct, signed, signed_at, perfis(nome, nome_artistico, nome_completo)"
    ).eq("contract_id", contract_id).execute().data or []
    obra = sb.table("obras").select("nome").eq("id", c["obra_id"]).single().execute().data or {}
    c["signers"] = signers
    c["obra_nome"] = obra.get("nome")
    return jsonify(c), 200


@contratos_lic_bp.route("/<contract_id>/aceitar", methods=["POST"])
@require_auth
@limiter.limit("30 per hour")
def aceitar(contract_id):
    data = request.get_json(force=True, silent=True) or {}
    if not data.get("concordo"):
        abort(422, description='Você precisa marcar "Li e concordo com os termos".')

    sb = get_supabase()
    c = _user_tem_acesso(sb, contract_id, g.user.id)
    if not c:
        abort(404, description="Contrato não encontrado.")
    if c["status"] == "cancelado":
        abort(409, description="Este contrato foi cancelado.")

    try:
        out = aceitar_contrato(contract_id, g.user.id, ip_hash=hash_ip(request.remote_addr or ""))
    except ValueError as e:
        abort(422, description=str(e))
    return jsonify({"ok": True, **out}), 200


@contratos_lic_bp.route("/<contract_id>/pdf", methods=["GET"])
@require_auth
@limiter.limit("10 per hour")
def pdf(contract_id):
    sb = get_supabase()
    c = _user_tem_acesso(sb, contract_id, g.user.id)
    if not c:
        abort(404, description="Contrato não encontrado.")

    # Adapta para a função gerar_pdf_contrato
    doc_dict = {
        "id":            c["id"],
        "obra_id":       c["obra_id"],
        "versao":        c.get("versao", "v1.0"),
        "assinado_em":   c.get("completed_at") or c.get("created_at"),
        "ip_assinatura": "—",
        "dados_titular": {"conteudo_hash": ""},
        "conteudo":      c["contract_text"],
    }
    pdf_bytes = gerar_pdf_contrato(doc_dict)
    buf = io.BytesIO(pdf_bytes); buf.seek(0)
    return send_file(
        buf, mimetype="application/pdf", as_attachment=True,
        download_name=f"contrato-licenciamento-{c['id'][:8]}.pdf",
    )


@contratos_lic_bp.route("/<contract_id>/dossie-licenca", methods=["GET"])
@require_auth
@limiter.limit("10 per hour")
def dossie_licenca(contract_id):
    """
    Faz o download do ZIP "Dossiê de Licença" — apenas o COMPRADOR pode baixar.
    Inclui: Letra (PDF premium com logo), áudio MP3 e cópia do contrato.
    """
    try:
        zip_bytes, filename = gerar_zip_dossie_licenca(contract_id, g.user.id)
    except PermissionError as e:
        abort(403, description=str(e))
    except ValueError as e:
        abort(404, description=str(e))
    except Exception as e:
        logger.exception("dossie_licenca: erro inesperado para contrato %s", contract_id)
        abort(500, description=f"Falha ao gerar Dossiê de Licença: {e}")

    return send_file(
        io.BytesIO(zip_bytes),
        mimetype="application/zip",
        as_attachment=True,
        download_name=filename,
    )


@contratos_lic_bp.route("/by-transacao/<transacao_id>", methods=["GET"])
@require_auth
def por_transacao(transacao_id):
    """
    Devolve o contrato associado a uma transação. Se o contrato ainda não tiver
    sido criado (webhook atrasado), tenta gerá-lo on-demand. Apenas o comprador
    ou o vendedor da transação podem consultar.
    """
    sb = get_supabase()
    tx = sb.table("transacoes").select(
        "id, status, comprador_id, obra_id, obras(titular_id)"
    ).eq("id", transacao_id).limit(1).execute()
    if not tx.data:
        abort(404, description="Transação não encontrada.")
    t = tx.data[0]
    titular_id = (t.get("obras") or {}).get("titular_id")
    if g.user.id not in {t.get("comprador_id"), titular_id}:
        abort(403, description="Sem acesso a esta transação.")

    # Já existe contrato?
    c = sb.table("contracts").select(
        "id, status, buyer_id, seller_id, trilateral"
    ).eq("transacao_id", transacao_id).limit(1).execute()

    if not c.data and t.get("status") == "confirmada":
        # Tenta gerar o contrato agora (caso o webhook não tenha rodado)
        try:
            from services.contrato_licenciamento import gerar_contrato_licenciamento
            gerar_contrato_licenciamento(transacao_id)
            c = sb.table("contracts").select(
                "id, status, buyer_id, seller_id, trilateral"
            ).eq("transacao_id", transacao_id).limit(1).execute()
        except Exception as e:
            logger.warning("por_transacao: falha ao gerar contrato on-demand %s: %s", transacao_id, e)

    if not c.data:
        return jsonify({"contract_id": None, "disponivel": False}), 200

    contract = c.data[0]
    sou_comprador = contract.get("buyer_id") == g.user.id
    return jsonify({
        "contract_id":   contract["id"],
        "status":        contract.get("status"),
        "trilateral":    contract.get("trilateral", False),
        "sou_comprador": sou_comprador,
        "disponivel":    True,
    }), 200


@contratos_lic_bp.route("/sincronizar", methods=["POST"])
@require_auth
@limiter.limit("20 per hour")
def sincronizar():
    """
    Varre todas as transações confirmadas onde o usuário é COMPRADOR ou
    TITULAR da obra, e gera os contratos faltantes. Útil em ambientes
    onde o webhook do Stripe não alcança o backend (localhost).
    """
    from services.contrato_licenciamento import gerar_contrato_licenciamento
    sb = get_supabase()

    # 1. Transações onde sou comprador
    tx_buyer = sb.table("transacoes").select("id").eq("comprador_id", g.user.id).eq("status", "confirmada").execute().data or []
    # 2. Transações onde sou titular da obra (vendedor)
    obras_minhas = sb.table("obras").select("id").eq("titular_id", g.user.id).execute().data or []
    obras_ids = [o["id"] for o in obras_minhas]
    tx_seller = []
    if obras_ids:
        tx_seller = sb.table("transacoes").select("id").in_("obra_id", obras_ids).eq("status", "confirmada").execute().data or []

    # 3. Coautorias (sou coautor de alguma obra vendida)
    coaut = sb.table("coautorias").select("obra_id").eq("perfil_id", g.user.id).execute().data or []
    obras_coaut = list({c["obra_id"] for c in coaut} - set(obras_ids))
    tx_coaut = []
    if obras_coaut:
        tx_coaut = sb.table("transacoes").select("id").in_("obra_id", obras_coaut).eq("status", "confirmada").execute().data or []

    todos_ids = list({t["id"] for t in (tx_buyer + tx_seller + tx_coaut)})
    if not todos_ids:
        return jsonify({"sincronizados": 0, "total_transacoes": 0}), 200

    # 4. Quais já têm contrato?
    existentes = sb.table("contracts").select("transacao_id").in_("transacao_id", todos_ids).execute().data or []
    ja_feitos = {e["transacao_id"] for e in existentes}
    faltando = [t for t in todos_ids if t not in ja_feitos]

    criados = 0
    erros = []
    for tid in faltando:
        try:
            c = gerar_contrato_licenciamento(tid)
            if c: criados += 1
        except Exception as e:
            erros.append({"transacao_id": tid, "erro": str(e)[:100]})

    return jsonify({
        "sincronizados": criados,
        "total_transacoes": len(todos_ids),
        "ja_existiam": len(ja_feitos),
        "erros": erros,
    }), 200
