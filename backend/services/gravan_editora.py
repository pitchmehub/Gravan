"""
Gravan Editora Operacional
==========================
UUID fixo do perfil de sistema da Gravan como Editora Detentora dos Direitos.

Quando um compositor cadastra uma obra SEM editora parceira:
  1. A obra é vinculada a este perfil (publisher_id + gravan_editora_id)
  2. O contrato de edição é gerado em contracts_edicao e auto-aceito pela
     plataforma no mesmo instante (status='assinado', ambos os signed_at preenchidos)
  3. O compositor vê "Gravan Editora" como sua editora no dashboard
"""
import hashlib
from datetime import datetime, timezone

from db.supabase_client import get_supabase
from utils.crypto import decrypt_pii

GRAVAN_EDITORA_UUID   = "e96bd8af-dfb8-4bf1-9ba5-7746207269cd"
GRAVAN_RAZAO_SOCIAL   = "GRAVAN EDITORA MUSICAL LTDA."
GRAVAN_CNPJ           = "64.342.514/0001-08"
GRAVAN_ENDERECO       = "Rio de Janeiro/RJ"
GRAVAN_EMAIL          = "editora@gravan.com.br"


def get_gravan_editora_perfil() -> dict:
    return {
        "id":                    GRAVAN_EDITORA_UUID,
        "nome":                  "Gravan Editora Musical",
        "razao_social":          GRAVAN_RAZAO_SOCIAL,
        "nome_fantasia":         "Gravan Editora",
        "cnpj":                  GRAVAN_CNPJ,
        "email":                 GRAVAN_EMAIL,
        "endereco_cidade":       "Rio de Janeiro",
        "endereco_uf":           "RJ",
        "is_gravan_operacional": True,
        "role":                  "publisher",
    }


def vincular_obra_gravan_editora(obra_id: str) -> bool:
    """Vincula uma obra à Gravan Editora Operacional."""
    sb = get_supabase()
    try:
        sb.table("obras").update({
            "publisher_id":         GRAVAN_EDITORA_UUID,
            "gravan_editora_id":    GRAVAN_EDITORA_UUID,
            "managed_by_publisher": True,
        }).eq("id", obra_id).execute()
        return True
    except Exception as e:
        print(f"[gravan_editora] falha ao vincular obra {obra_id}: {e}")
        return False


def gerar_contrato_gravan_editora(
    obra_id:    str,
    autor_id:   str,
    perfil:     dict,
    obra_nome:  str,
    obra_letra: str,
    coautorias: list,
    ip_hashed:  str,
    versao:     str = "v2.9 - Abr/2026",
) -> dict | None:
    """
    Gera e auto-assina o contrato de edição Gravan Editora ↔ Autor.
    Usa contracts_edicao com status='assinado' e ambos signed_at preenchidos.
    Idempotente: se já existe contrato para o par (obra_id, autor_id), retorna o existente.
    """
    sb = get_supabase()

    # Idempotência
    existing = (
        sb.table("contracts_edicao")
        .select("*")
        .eq("obra_id", obra_id)
        .eq("autor_id", autor_id)
        .maybe_single()
        .execute()
    )
    if existing and existing.data:
        return existing.data

    # Carrega template do banco ou fallback do módulo
    tpl_row = (
        sb.table("landing_content")
        .select("valor")
        .eq("id", "contrato_edicao_template")
        .maybe_single()
        .execute()
    )
    from services.contrato_template import CONTRATO_TEMPLATE
    tpl_texto = (
        ((tpl_row.data or {}).get("valor") if tpl_row and tpl_row.data else None)
        or CONTRATO_TEMPLATE
    )

    # Dados do autor
    cpf_dec  = decrypt_pii(perfil.get("cpf", "")) or ""
    rg_dec   = decrypt_pii(perfil.get("rg",  "")) or ""
    endereco = ", ".join(filter(None, [
        perfil.get("endereco_rua"),
        perfil.get("endereco_numero"),
        perfil.get("endereco_compl"),
        perfil.get("endereco_bairro"),
        perfil.get("endereco_cidade"),
        perfil.get("endereco_uf"),
        f"CEP {perfil['endereco_cep']}" if perfil.get("endereco_cep") else None,
    ])) or "Não informado"

    # Share e coautores
    share_autor = 100.0
    coautores_str = "autoria única"
    try:
        titular_entry = next((c for c in coautorias if c.get("perfil_id") == autor_id), None)
        if titular_entry:
            share_autor = float(titular_entry.get("share_pct", 100))
        outros_ids = [c["perfil_id"] for c in coautorias if c.get("perfil_id") != autor_id]
        if outros_ids:
            outros = sb.table("perfis").select("id, nome_completo, nome").in_("id", outros_ids).execute()
            mapa = {p["id"]: (p.get("nome_completo") or p.get("nome") or "Coautor") for p in (outros.data or [])}
            partes = []
            for c in coautorias:
                if c.get("perfil_id") == autor_id:
                    continue
                nm = mapa.get(c["perfil_id"], "Coautor")
                partes.append(f"{nm} ({float(c['share_pct']):.2f}%)")
            coautores_str = "; ".join(partes) if partes else "autoria única"
    except Exception:
        pass

    agora_str = datetime.now(timezone.utc).strftime("%d/%m/%Y às %H:%M UTC")

    texto = (
        tpl_texto
        .replace("{{nome_completo}}",           perfil.get("nome_completo") or perfil.get("nome") or "")
        .replace("{{cpf}}",                     cpf_dec)
        .replace("{{rg}}",                      rg_dec)
        .replace("{{endereco_completo}}",       endereco)
        .replace("{{email}}",                   perfil.get("email") or "")
        .replace("{{data_assinatura}}",         agora_str)
        .replace("{{obra_nome}}",               obra_nome)
        .replace("{{obra_letra}}",              (obra_letra or "").strip() or "—")
        .replace("{{share_autor_pct}}",         f"{share_autor:.2f}".rstrip("0").rstrip("."))
        .replace("{{coautores_lista}}",         coautores_str)
        .replace("{{plataforma_razao_social}}", GRAVAN_RAZAO_SOCIAL)
        .replace("{{plataforma_cnpj}}",         GRAVAN_CNPJ)
        .replace("{{plataforma_endereco}}",     GRAVAN_ENDERECO)
    )

    conteudo_hash = hashlib.sha256(texto.encode("utf-8")).hexdigest()
    texto = texto.replace("{{conteudo_hash}}", conteudo_hash)

    html = (
        "<pre style='white-space:pre-wrap;font-family:Georgia,serif;"
        "font-size:14px;line-height:1.6'>"
        + texto.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        + "</pre>"
    )

    now_iso = datetime.now(timezone.utc).isoformat()

    row = {
        "obra_id":               obra_id,
        "publisher_id":          GRAVAN_EDITORA_UUID,
        "autor_id":              autor_id,
        "share_pct":             float(share_autor),
        "contract_html":         html,
        "contract_text":         texto,
        "has_fee_clause":        True,
        "conteudo_hash":         conteudo_hash,
        "status":                "assinado",
        "versao":                versao,
        "signed_by_publisher_at": now_iso,
        "signed_by_autor_at":    now_iso,
        "publisher_ip_hash":     "gravan-operacional-auto",
        "autor_ip_hash":         ip_hashed,
        "completed_at":          now_iso,
    }

    try:
        res = sb.table("contracts_edicao").insert(row).execute()
        contrato = (res.data or [{}])[0]
        try:
            from utils.audit import log_event
            log_event(
                "contrato.gerado_gravan_editora",
                entity_type="contract_edicao",
                entity_id=contrato.get("id"),
                metadata={"obra_id": obra_id, "autor_id": autor_id,
                          "auto_aceito": True, "gravan_operacional": True},
            )
        except Exception:
            pass
        return contrato
    except Exception as e:
        print(f"[gravan_editora] falha ao inserir contrato: {e}")
        return None
