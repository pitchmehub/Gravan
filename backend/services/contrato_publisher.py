"""
Geração do Contrato de Edição entre EDITORA e AUTOR.
Disparado automaticamente quando uma obra com publisher_id é cadastrada.
Aplica cláusula de fee 5% com dados bancários da GRAVAN (de landing_content).
"""
import hashlib
import json
from datetime import datetime, timezone

from db.supabase_client import get_supabase
from utils.audit import log_event
from utils.crypto import decrypt_pii


FALLBACK_BANCARIOS = {
    "razao_social": "GRAVAN", "cnpj": "[PREENCHER]",
    "banco": "[PREENCHER]", "agencia": "[PREENCHER]",
    "conta": "[PREENCHER]", "titular": "GRAVAN",
}


def _load_template(sb) -> str:
    r = sb.table("landing_content").select("valor").eq("id", "contrato_edicao_publisher_template").maybe_single().execute()
    return (r.data or {}).get("valor") if r and r.data else None


def _load_bancarios(sb) -> dict:
    r = sb.table("landing_content").select("valor").eq("id", "gravan_dados_bancarios").maybe_single().execute()
    raw = (r.data or {}).get("valor") if r and r.data else None
    if not raw:
        return FALLBACK_BANCARIOS
    try:
        return json.loads(raw)
    except Exception:
        return FALLBACK_BANCARIOS


def _endereco_completo(p: dict) -> str:
    parts = [
        p.get("endereco_rua"), p.get("endereco_numero"),
        p.get("endereco_compl"), p.get("endereco_bairro"),
        p.get("endereco_cidade"), p.get("endereco_uf"),
        p.get("endereco_cep"),
    ]
    return ", ".join([x for x in parts if x]) or "Não informado"


def _decrypt_safe(v):
    if not v: return ""
    try: return decrypt_pii(v) or v
    except Exception: return v


def gerar_contrato_edicao(obra_id: str, autor_id: str, publisher_id: str) -> dict | None:
    """
    Gera contrato de edição autor↔editora. Idempotente: se já existe contrato
    pra esse par (obra, autor), retorna o existente sem recriar.
    """
    sb = get_supabase()

    existente = sb.table("contracts_edicao").select("*").eq("obra_id", obra_id).eq("autor_id", autor_id).maybe_single().execute()
    if existente and existente.data:
        return existente.data

    obra = sb.table("obras").select("*").eq("id", obra_id).single().execute().data
    autor = sb.table("perfis").select("*").eq("id", autor_id).single().execute().data
    publisher = sb.table("perfis").select("*").eq("id", publisher_id).single().execute().data

    coautores_q = sb.table("coautorias").select("perfil_id,share_pct").eq("obra_id", obra_id).execute()
    coautores_ids = [c["perfil_id"] for c in (coautores_q.data or []) if c["perfil_id"] != autor_id]
    share_autor = next((c["share_pct"] for c in (coautores_q.data or []) if c["perfil_id"] == autor_id), 100)

    coautores_nomes = []
    if coautores_ids:
        cs = sb.table("perfis").select("id,nome_completo,nome_artistico").in_("id", coautores_ids).execute()
        for c in (cs.data or []):
            coautores_nomes.append(c.get("nome_artistico") or c.get("nome_completo") or "—")
    coautores_lista = "; ".join(coautores_nomes) if coautores_nomes else "Nenhum"

    template = _load_template(sb) or ""
    bancarios = _load_bancarios(sb)

    contexto = {
        "autor_nome":     autor.get("nome_completo") or "",
        "autor_rg":       _decrypt_safe(autor.get("rg")),
        "autor_cpf":      _decrypt_safe(autor.get("cpf")),
        "autor_endereco": _endereco_completo(autor),
        "autor_email":    autor.get("email") or "",
        "publisher_razao_social":     publisher.get("razao_social") or "",
        "publisher_nome_fantasia":    publisher.get("nome_fantasia") or "",
        "publisher_cnpj":             _decrypt_safe(publisher.get("cnpj")),
        "publisher_endereco":         _endereco_completo(publisher),
        "publisher_responsavel_nome": publisher.get("responsavel_nome") or "",
        "publisher_responsavel_cpf":  _decrypt_safe(publisher.get("responsavel_cpf")),
        "share_autor_pct":  f"{float(share_autor):.2f}",
        "obra_nome":        obra.get("titulo") or obra.get("nome") or "",
        "obra_letra":       (obra.get("letra") or "").strip() or "—",
        "coautores_lista":  coautores_lista,
        "gravan_banco":    bancarios.get("banco", "[PREENCHER]"),
        "gravan_agencia":  bancarios.get("agencia", "[PREENCHER]"),
        "gravan_conta":    bancarios.get("conta", "[PREENCHER]"),
        "gravan_titular":  bancarios.get("titular", "GRAVAN"),
        "gravan_cnpj":     bancarios.get("cnpj", "[PREENCHER]"),
        "data_emissao":     datetime.now(timezone.utc).strftime("%d/%m/%Y"),
    }

    texto = template
    for k, v in contexto.items():
        texto = texto.replace("{{" + k + "}}", str(v))

    conteudo_hash = hashlib.sha256(texto.encode("utf-8")).hexdigest()
    texto = texto.replace("{{conteudo_hash}}", conteudo_hash)

    html = "<pre style='white-space:pre-wrap;font-family:Georgia,serif;font-size:14px;line-height:1.6'>" + \
           texto.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;") + "</pre>"

    novo = sb.table("contracts_edicao").insert({
        "obra_id":        obra_id,
        "publisher_id":   publisher_id,
        "autor_id":       autor_id,
        "share_pct":      float(share_autor),
        "contract_html":  html,
        "contract_text":  texto,
        "has_fee_clause": True,
        "conteudo_hash":  conteudo_hash,
        "status":         "pendente",
    }).execute()

    contrato = (novo.data or [{}])[0]
    log_event("contrato.gerado", entity_type="contract_edicao", entity_id=contrato.get("id"),
              metadata={"obra_id": obra_id, "autor_id": autor_id, "publisher_id": publisher_id})
    return contrato
