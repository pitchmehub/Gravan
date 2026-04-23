"""Routes: /api/contratos/licenciamento — contratos de gravação/exploração."""
import io
from flask import Blueprint, request, jsonify, g, abort, send_file
from middleware.auth import require_auth
from db.supabase_client import get_supabase
from services.contrato_licenciamento import aceitar_contrato
from services.contrato_pdf import gerar_pdf_contrato
from utils.crypto import hash_ip
from app import limiter

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
