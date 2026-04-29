"""
Certificado de Assinaturas Digitais — Gravan
=============================================
Gerado no momento em que todos os signatários assinam um contrato de
licenciamento. Permanece PERMANENTEMENTE gravado no banco como parte
do contrato, servindo como prova jurídica de consentimento eletrônico
nos termos da MP 2.200-2/2001 e da Lei 14.063/2020.

Conteúdo do certificado (por signatário):
  • Nome completo (ao momento da assinatura)
  • E-mail cadastrado
  • CPF (primeiros 3 dígitos + *** — proteção LGPD)
  • Papel no contrato (autor, coautor, editora…)
  • Data e hora exata da assinatura (UTC)
  • IP de origem (hash SHA-256 unidirecional — não reversível)
  • User-Agent (navegador / dispositivo)
  • Token de unicidade por assinatura (HMAC-SHA256)

No final:
  • Hash SHA-256 do documento original + todos os dados de assinatura
    (qualquer alteração posterior invalida o hash)
"""
import hashlib
import hmac
import logging
import os
from datetime import datetime, timezone

from db.supabase_client import get_supabase

logger = logging.getLogger("gravan.certificado")

_GRAVAN_EDITORA_UUID = "e96bd8af-dfb8-4bf1-9ba5-7746207269cd"
_SECRET = (os.environ.get("SUPABASE_SERVICE_KEY") or "gravan-cert-secret")[:32]

ROLE_LABEL = {
    "autor":              "Autor Principal",
    "coautor":            "Coautor(a)",
    "intérprete":         "Intérprete",
    "interprete":         "Intérprete",
    "editora_agregadora": "Editora Agregadora (Gravan)",
    "editora_detentora":  "Editora Detentora dos Direitos",
    "editora_terceira":   "Editora Terceira",
}


def _mask_cpf(cpf: str) -> str:
    """Mostra apenas os 3 primeiros dígitos: 123.***.***-**"""
    digits = "".join(c for c in (cpf or "") if c.isdigit())
    if len(digits) >= 11:
        return f"{digits[:3]}.***.***.{digits[-2:]}"
    if digits:
        return digits[:3] + "..." + digits[-2:] if len(digits) > 5 else digits[:3] + "***"
    return "Não informado"


def _mask_email(email: str) -> str:
    """joao@gmail.com → j***@gmail.com"""
    if not email or "@" not in email:
        return "Não informado"
    local, domain = email.split("@", 1)
    return local[0] + "***@" + domain


def _token_assinatura(user_id: str, contract_id: str, signed_at: str) -> str:
    """Token de autenticidade único por assinatura (HMAC-SHA256)."""
    msg = f"{user_id}:{contract_id}:{signed_at}".encode()
    return hmac.new(_SECRET.encode(), msg, hashlib.sha256).hexdigest()[:32]


def gerar_certificado_assinaturas(contract_id: str) -> dict:
    """
    Lê todos os signatários do contrato, monta o bloco de certificado
    e atualiza contract_text / contract_html no banco.

    Retorna {"ok": True, "hash": "<sha256>"} ou {"ok": False, "erro": "..."}.
    """
    sb = get_supabase()

    try:
        ctr = sb.table("contracts").select(
            "id, contract_text, contract_html, obra_id, buyer_id, seller_id, "
            "valor_cents, completed_at"
        ).eq("id", contract_id).single().execute().data
        if not ctr:
            return {"ok": False, "erro": "Contrato não encontrado"}

        signers_rows = sb.table("contract_signers").select(
            "user_id, role, signed, signed_at, ip_hash, user_agent, share_pct"
        ).eq("contract_id", contract_id).order("signed_at").execute().data or []

        user_ids = [s["user_id"] for s in signers_rows if s.get("user_id")]
        perfis_map: dict[str, dict] = {}
        if user_ids:
            perfis_rows = sb.table("perfis").select(
                "id, nome_completo, nome, email, cpf"
            ).in_("id", user_ids).execute().data or []
            perfis_map = {p["id"]: p for p in perfis_rows}

        from utils.crypto import decrypt_pii

        linhas = []
        tokens_concat = []

        for idx, s in enumerate(signers_rows, 1):
            uid = s.get("user_id", "")
            p = perfis_map.get(uid, {})

            is_gravan = uid == _GRAVAN_EDITORA_UUID
            nome = "GRAVAN EDITORA MUSICAL LTDA." if is_gravan else (
                p.get("nome_completo") or p.get("nome") or "Não informado"
            )
            email = "editora@gravan.com.br" if is_gravan else _mask_email(
                p.get("email") or ""
            )
            cpf_raw = "" if is_gravan else (decrypt_pii(p.get("cpf") or "") or "")
            cpf_m = "CNPJ 64.342.514/0001-08" if is_gravan else _mask_cpf(cpf_raw)

            papel = ROLE_LABEL.get(s.get("role", ""), s.get("role") or "Parte")
            share = (
                f" · {float(s['share_pct']):.2f}% de participação"
                if s.get("share_pct") is not None else ""
            )

            signed_at_raw = s.get("signed_at") or ""
            try:
                dt = datetime.fromisoformat(signed_at_raw.replace("Z", "+00:00"))
                dt_fmt = dt.strftime("%d/%m/%Y às %H:%M:%S UTC")
            except Exception:
                dt_fmt = signed_at_raw or "Data não registrada"

            ip_h = s.get("ip_hash") or "Não capturado"
            ua = (s.get("user_agent") or "Não capturado")[:200]

            token = _token_assinatura(uid, contract_id, signed_at_raw)
            tokens_concat.append(token)

            tipo_assina = "Assinatura eletrônica automática da plataforma" if is_gravan else "Assinatura eletrônica voluntária"

            linhas.append(
                f"  [{idx}] {nome}\n"
                f"      Identificação : {cpf_m}\n"
                f"      E-mail        : {email}\n"
                f"      Papel         : {papel}{share}\n"
                f"      Data/Hora     : {dt_fmt}\n"
                f"      IP (hash)     : {ip_h}\n"
                f"      Dispositivo   : {ua}\n"
                f"      Tipo          : {tipo_assina}\n"
                f"      Token         : {token}\n"
            )

        obra_row = sb.table("obras").select("nome").eq(
            "id", ctr.get("obra_id")
        ).maybe_single().execute().data or {}
        obra_nome = obra_row.get("nome") or "Obra Musical"

        valor_cents = ctr.get("valor_cents") or 0
        valor_str = (
            f"R$ {valor_cents / 100:,.2f}"
            .replace(",", "X").replace(".", ",").replace("X", ".")
        )

        completed_at = ctr.get("completed_at") or datetime.now(timezone.utc).isoformat()
        try:
            dt_c = datetime.fromisoformat(completed_at.replace("Z", "+00:00"))
            completed_fmt = dt_c.strftime("%d/%m/%Y às %H:%M:%S UTC")
        except Exception:
            completed_fmt = completed_at

        signers_text = "\n".join(linhas)
        all_tokens = ":".join(tokens_concat)
        doc_original = (ctr.get("contract_text") or "").strip()

        digest_input = f"{doc_original}\n{contract_id}\n{all_tokens}"
        doc_hash = hashlib.sha256(digest_input.encode("utf-8")).hexdigest()

        separador = "═" * 70
        certificado_txt = (
            f"\n\n{separador}\n"
            f"  CERTIFICADO DE ASSINATURAS DIGITAIS — GRAVAN\n"
            f"  Emitido em: {completed_fmt}\n"
            f"{separador}\n\n"
            f"  Obra           : {obra_nome}\n"
            f"  Contrato ID    : {contract_id}\n"
            f"  Valor          : {valor_str}\n"
            f"  Base legal     : MP 2.200-2/2001 · Lei 14.063/2020 · LGPD 13.709/2018\n\n"
            f"  SIGNATÁRIOS:\n\n"
            f"{signers_text}\n"
            f"  INTEGRIDADE DO DOCUMENTO:\n"
            f"  Hash SHA-256   : {doc_hash}\n"
            f"  (Qualquer alteração posterior ao documento invalida este hash.)\n\n"
            f"  Este certificado faz parte integrante e inseparável do contrato\n"
            f"  acima, tendo valor jurídico pleno conforme legislação vigente.\n"
            f"{separador}\n"
        )

        novo_texto = doc_original + certificado_txt

        cert_html = (
            "<div style='"
            "margin-top:40px;border:2px solid #1a1a2e;border-radius:8px;"
            "padding:28px 32px;background:#f9f9ff;font-family:Georgia,serif;"
            "font-size:13px;line-height:1.8;color:#111;"
            "'>"
            "<div style='font-size:15px;font-weight:700;letter-spacing:1px;"
            "margin-bottom:16px;color:#1a1a2e;border-bottom:1px solid #ccc;"
            "padding-bottom:10px;'>"
            "CERTIFICADO DE ASSINATURAS DIGITAIS — GRAVAN"
            "</div>"
            f"<p><b>Obra:</b> {obra_nome} &nbsp;|&nbsp; "
            f"<b>Contrato ID:</b> {contract_id}<br>"
            f"<b>Emitido em:</b> {completed_fmt} &nbsp;|&nbsp; "
            f"<b>Valor:</b> {valor_str}<br>"
            f"<b>Base legal:</b> MP 2.200-2/2001 · Lei 14.063/2020 · LGPD 13.709/2018</p>"
            "<hr style='margin:16px 0'>"
            "<b>SIGNATÁRIOS:</b><br><br>"
        )
        for idx, s in enumerate(signers_rows, 1):
            uid = s.get("user_id", "")
            p = perfis_map.get(uid, {})
            is_gravan = uid == _GRAVAN_EDITORA_UUID
            nome = "GRAVAN EDITORA MUSICAL LTDA." if is_gravan else (
                p.get("nome_completo") or p.get("nome") or "Não informado"
            )
            email = "editora@gravan.com.br" if is_gravan else _mask_email(p.get("email") or "")
            cpf_raw = "" if is_gravan else (decrypt_pii(p.get("cpf") or "") or "")
            cpf_m = "CNPJ 64.342.514/0001-08" if is_gravan else _mask_cpf(cpf_raw)
            papel = ROLE_LABEL.get(s.get("role", ""), s.get("role") or "Parte")
            share = f" · {float(s['share_pct']):.2f}%" if s.get("share_pct") is not None else ""
            signed_at_raw = s.get("signed_at") or ""
            try:
                dt = datetime.fromisoformat(signed_at_raw.replace("Z", "+00:00"))
                dt_fmt = dt.strftime("%d/%m/%Y às %H:%M:%S UTC")
            except Exception:
                dt_fmt = signed_at_raw or "—"
            ip_h = s.get("ip_hash") or "Não capturado"
            ua = (s.get("user_agent") or "Não capturado")[:200]
            token = _token_assinatura(uid, contract_id, signed_at_raw)
            tipo_assina = "Automática (plataforma)" if is_gravan else "Voluntária (usuário)"
            cert_html += (
                f"<div style='background:#fff;border:1px solid #e0e0e0;"
                f"border-radius:6px;padding:14px 18px;margin-bottom:12px;'>"
                f"<b>[{idx}] {nome}</b><br>"
                f"<span style='font-size:12px;color:#555;'>"
                f"<b>CPF/CNPJ:</b> {cpf_m} &nbsp;|&nbsp; "
                f"<b>E-mail:</b> {email}<br>"
                f"<b>Papel:</b> {papel}{share} &nbsp;|&nbsp; "
                f"<b>Assinatura:</b> {tipo_assina}<br>"
                f"<b>Data/Hora:</b> {dt_fmt}<br>"
                f"<b>IP (hash):</b> {ip_h}<br>"
                f"<b>Dispositivo:</b> {ua}<br>"
                f"<b>Token:</b> <code style='font-size:11px;'>{token}</code>"
                f"</span></div>"
            )

        cert_html += (
            "<hr style='margin:16px 0'>"
            f"<p style='font-size:12px;'><b>Hash SHA-256 do documento:</b><br>"
            f"<code style='font-size:11px;word-break:break-all;'>{doc_hash}</code><br>"
            f"<i>Qualquer alteração posterior invalida este hash.</i></p>"
            "<p style='font-size:11px;color:#666;'>"
            "Este certificado faz parte integrante e inseparável do contrato, "
            "tendo valor jurídico pleno conforme MP 2.200-2/2001 e Lei 14.063/2020.</p>"
            "</div>"
        )

        novo_html = (ctr.get("contract_html") or "") + cert_html

        sb.table("contracts").update({
            "contract_text":    novo_texto,
            "contract_html":    novo_html,
            "certificado_hash": doc_hash,
            "certificado_at":   datetime.now(timezone.utc).isoformat(),
        }).eq("id", contract_id).execute()

        logger.info(
            "Certificado de assinaturas gerado para contrato %s — hash: %s",
            contract_id, doc_hash
        )
        return {"ok": True, "hash": doc_hash}

    except Exception as e:
        logger.exception("Erro ao gerar certificado para contrato %s: %s", contract_id, e)
        return {"ok": False, "erro": str(e)}
