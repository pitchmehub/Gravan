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


# ══════════════════════════════════════════════════════════════════
# CERTIFICADO — CONTRATO DE EDIÇÃO (contracts_edicao)
# ══════════════════════════════════════════════════════════════════
def gerar_certificado_edicao(contract_edicao_id: str) -> dict:
    """
    Gera o Certificado de Assinaturas Digitais para um Contrato de Edição
    (autor ↔ editora/Gravan) e grava em contracts_edicao.certificado_html.

    Chamado assim que ambas as partes assinam (status='assinado').
    Base legal: MP 2.200-2/2001 · Lei 14.063/2020 · LGPD 13.709/2018.
    """
    sb = get_supabase()
    try:
        c = sb.table("contracts_edicao").select(
            "id, obra_id, autor_id, publisher_id, share_pct, "
            "contract_text, contract_html, "
            "signed_by_autor_at, autor_ip_hash, "
            "signed_by_publisher_at, publisher_ip_hash, "
            "completed_at, versao"
        ).eq("id", contract_edicao_id).single().execute().data
        if not c:
            return {"ok": False, "erro": "Contrato de edição não encontrado"}

        from utils.crypto import decrypt_pii

        # ── Perfil do publisher ──
        pub = sb.table("perfis").select(
            "id, nome_completo, nome, razao_social, nome_fantasia, email, cpf, cnpj"
        ).eq("id", c["publisher_id"]).single().execute().data or {}
        is_gravan_pub = (c["publisher_id"] == _GRAVAN_EDITORA_UUID)
        pub_nome = "GRAVAN EDITORA MUSICAL LTDA." if is_gravan_pub else (
            pub.get("razao_social") or pub.get("nome_fantasia") or
            pub.get("nome_completo") or pub.get("nome") or "Editora"
        )
        pub_email = "editora@gravan.com.br" if is_gravan_pub else _mask_email(pub.get("email") or "")
        pub_cnpj_raw = "" if is_gravan_pub else (decrypt_pii(pub.get("cnpj") or "") or "")
        pub_doc = "CNPJ 64.342.514/0001-08" if is_gravan_pub else (
            "CNPJ " + pub_cnpj_raw[:18] if pub_cnpj_raw else
            _mask_cpf(decrypt_pii(pub.get("cpf") or "") or "")
        )
        pub_signed_raw = c.get("signed_by_publisher_at") or c.get("completed_at") or ""
        pub_ip = c.get("publisher_ip_hash") or "Assinatura automática da plataforma"
        pub_token = _token_assinatura(c["publisher_id"], contract_edicao_id, pub_signed_raw)

        # ── Perfil do autor ──
        aut = sb.table("perfis").select(
            "id, nome_completo, nome, email, cpf"
        ).eq("id", c["autor_id"]).single().execute().data or {}
        aut_nome = aut.get("nome_completo") or aut.get("nome") or "Compositor(a)"
        aut_email = _mask_email(aut.get("email") or "")
        aut_cpf = _mask_cpf(decrypt_pii(aut.get("cpf") or "") or "")
        aut_signed_raw = c.get("signed_by_autor_at") or ""
        aut_ip = c.get("autor_ip_hash") or "Não capturado"
        aut_token = _token_assinatura(c["autor_id"], contract_edicao_id, aut_signed_raw)

        # ── Obra ──
        obra = sb.table("obras").select("nome").eq(
            "id", c["obra_id"]
        ).maybe_single().execute().data or {}
        obra_nome = obra.get("nome") or "Obra Musical"
        share = f"{float(c['share_pct']):.2f}%" if c.get("share_pct") is not None else "—"

        # ── Datas formatadas ──
        def _fmt(raw):
            if not raw:
                return "—"
            try:
                return datetime.fromisoformat(
                    raw.replace("Z", "+00:00")
                ).strftime("%d/%m/%Y às %H:%M:%S UTC")
            except Exception:
                return raw

        completed_fmt = _fmt(c.get("completed_at"))
        pub_signed_fmt = _fmt(pub_signed_raw) if pub_signed_raw else "Automático (plataforma)"
        aut_signed_fmt = _fmt(aut_signed_raw)

        # ── Hash do documento ──
        doc_text = (c.get("contract_text") or "").strip()
        digest_input = f"{doc_text}\n{contract_edicao_id}\n{pub_token}:{aut_token}"
        doc_hash = hashlib.sha256(digest_input.encode("utf-8")).hexdigest()

        separador = "═" * 70

        # ── Bloco texto ──
        cert_txt = (
            f"\n\n{separador}\n"
            f"  CERTIFICADO DE ASSINATURAS DIGITAIS — GRAVAN\n"
            f"  Emitido em: {completed_fmt}\n"
            f"{separador}\n\n"
            f"  Tipo           : Contrato de Edição Musical\n"
            f"  Obra           : {obra_nome}\n"
            f"  Contrato ID    : {contract_edicao_id}\n"
            f"  Participação   : {share}\n"
            f"  Base legal     : MP 2.200-2/2001 · Lei 14.063/2020 · LGPD 13.709/2018\n\n"
            f"  SIGNATÁRIOS:\n\n"
            f"  [1] {pub_nome}\n"
            f"      Identificação : {pub_doc}\n"
            f"      E-mail        : {pub_email}\n"
            f"      Papel         : Editora Parceira / Detentora dos Direitos\n"
            f"      Data/Hora     : {pub_signed_fmt}\n"
            f"      IP (hash)     : {pub_ip}\n"
            f"      Tipo          : {'Assinatura eletrônica automática da plataforma' if is_gravan_pub else 'Assinatura eletrônica voluntária'}\n"
            f"      Token         : {pub_token}\n\n"
            f"  [2] {aut_nome}\n"
            f"      Identificação : {aut_cpf}\n"
            f"      E-mail        : {aut_email}\n"
            f"      Papel         : Compositor(a) / Autor(a)\n"
            f"      Data/Hora     : {aut_signed_fmt}\n"
            f"      IP (hash)     : {aut_ip}\n"
            f"      Tipo          : Assinatura eletrônica voluntária\n"
            f"      Token         : {aut_token}\n\n"
            f"  INTEGRIDADE DO DOCUMENTO:\n"
            f"  Hash SHA-256   : {doc_hash}\n"
            f"  (Qualquer alteração posterior ao documento invalida este hash.)\n\n"
            f"  Este certificado faz parte integrante e inseparável do contrato\n"
            f"  acima, tendo valor jurídico pleno conforme legislação vigente.\n"
            f"{separador}\n"
        )

        # ── Bloco HTML ──
        def _signer_card(idx, nome, doc, email, papel, signed_fmt, ip_h, tipo, token):
            return (
                f"<div style='background:#fff;border:1px solid #e0e0e0;"
                f"border-radius:6px;padding:14px 18px;margin-bottom:12px;'>"
                f"<b>[{idx}] {nome}</b><br>"
                f"<span style='font-size:12px;color:#555;'>"
                f"<b>CPF/CNPJ:</b> {doc} &nbsp;|&nbsp; <b>E-mail:</b> {email}<br>"
                f"<b>Papel:</b> {papel}<br>"
                f"<b>Assinatura:</b> {tipo}<br>"
                f"<b>Data/Hora:</b> {signed_fmt}<br>"
                f"<b>IP (hash):</b> {ip_h}<br>"
                f"<b>Token:</b> <code style='font-size:11px;'>{token}</code>"
                f"</span></div>"
            )

        cert_html = (
            "<div style='margin-top:40px;border:2px solid #1a1a2e;border-radius:8px;"
            "padding:28px 32px;background:#f9f9ff;font-family:Georgia,serif;"
            "font-size:13px;line-height:1.8;color:#111;'>"
            "<div style='font-size:15px;font-weight:700;letter-spacing:1px;"
            "margin-bottom:16px;color:#1a1a2e;border-bottom:1px solid #ccc;"
            "padding-bottom:10px;'>CERTIFICADO DE ASSINATURAS DIGITAIS — GRAVAN</div>"
            f"<p><b>Tipo:</b> Contrato de Edição Musical<br>"
            f"<b>Obra:</b> {obra_nome} &nbsp;|&nbsp; <b>Participação:</b> {share}<br>"
            f"<b>Contrato ID:</b> {contract_edicao_id}<br>"
            f"<b>Emitido em:</b> {completed_fmt}<br>"
            f"<b>Base legal:</b> MP 2.200-2/2001 · Lei 14.063/2020 · LGPD 13.709/2018</p>"
            "<hr style='margin:16px 0'><b>SIGNATÁRIOS:</b><br><br>"
        )
        pub_tipo = "Automática (plataforma)" if is_gravan_pub else "Voluntária (editora)"
        cert_html += _signer_card(1, pub_nome, pub_doc, pub_email,
                                  "Editora Parceira / Detentora dos Direitos",
                                  pub_signed_fmt, pub_ip, pub_tipo, pub_token)
        cert_html += _signer_card(2, aut_nome, aut_cpf, aut_email,
                                  "Compositor(a) / Autor(a)",
                                  aut_signed_fmt, aut_ip, "Voluntária (usuário)", aut_token)
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

        novo_texto = doc_text + cert_txt
        novo_html = (c.get("contract_html") or "") + cert_html
        agora = datetime.now(timezone.utc).isoformat()

        sb.table("contracts_edicao").update({
            "contract_text":    novo_texto,
            "contract_html":    novo_html,
            "certificado_html": cert_html,
            "certificado_hash": doc_hash,
            "certificado_at":   agora,
        }).eq("id", contract_edicao_id).execute()

        logger.info(
            "Certificado de edição gerado para contrato %s — hash: %s",
            contract_edicao_id, doc_hash,
        )
        return {"ok": True, "hash": doc_hash}

    except Exception as e:
        logger.exception(
            "Erro ao gerar certificado de edição para contrato %s: %s",
            contract_edicao_id, e,
        )
        return {"ok": False, "erro": str(e)}


# ══════════════════════════════════════════════════════════════════
# CERTIFICADO — TERMO DE AGREGAÇÃO (agregado_convites)
# ══════════════════════════════════════════════════════════════════
def gerar_certificado_agregacao(convite_id: str) -> dict:
    """
    Gera o Certificado de Assinaturas Digitais para o Termo de Agregação
    (artista aceita vínculo com editora) e grava em agregado_convites.

    Chamado imediatamente após o artista aceitar o convite.
    Base legal: MP 2.200-2/2001 · Lei 14.063/2020 · LGPD 13.709/2018.
    """
    sb = get_supabase()
    try:
        cv = sb.table("agregado_convites").select(
            "id, editora_id, artista_id, email_artista, termo_html, termo_text, "
            "responsavel_editora_nome, responsavel_editora_cpf_mask, "
            "editora_aceito_em, editora_aceito_ip, "
            "termo_aceito_pelo_artista_em, termo_aceito_ip, "
            "assinatura_artista_nome, termo_versao, decided_at"
        ).eq("id", convite_id).single().execute().data
        if not cv:
            return {"ok": False, "erro": "Convite não encontrado"}

        from utils.crypto import decrypt_pii

        # ── Perfil da editora ──
        edit = sb.table("perfis").select(
            "id, nome_completo, nome, razao_social, nome_fantasia, email, cnpj, cpf"
        ).eq("id", cv["editora_id"]).single().execute().data or {}
        edit_nome = (
            edit.get("razao_social") or edit.get("nome_fantasia") or
            edit.get("nome_completo") or edit.get("nome") or "Editora"
        )
        edit_email = _mask_email(edit.get("email") or "")
        cnpj_raw = decrypt_pii(edit.get("cnpj") or "") or ""
        edit_doc = "CNPJ " + cnpj_raw[:18] if cnpj_raw else (
            _mask_cpf(decrypt_pii(edit.get("cpf") or "") or "")
        )
        edit_signed_raw = cv.get("editora_aceito_em") or ""
        edit_ip = cv.get("editora_aceito_ip") or "Não capturado"
        edit_token = _token_assinatura(cv["editora_id"], convite_id, edit_signed_raw)

        # ── Perfil do artista ──
        artista_id = cv.get("artista_id") or ""
        art = {}
        if artista_id:
            art = sb.table("perfis").select(
                "id, nome_completo, nome, email, cpf"
            ).eq("id", artista_id).maybe_single().execute().data or {}
        art_nome = (
            cv.get("assinatura_artista_nome") or
            art.get("nome_completo") or art.get("nome") or "Artista"
        )
        art_email = _mask_email(art.get("email") or cv.get("email_artista") or "")
        art_cpf = _mask_cpf(decrypt_pii(art.get("cpf") or "") or "")
        art_signed_raw = cv.get("termo_aceito_pelo_artista_em") or ""
        art_ip = cv.get("termo_aceito_ip") or "Não capturado"
        art_token = _token_assinatura(artista_id or cv["editora_id"], convite_id, art_signed_raw)

        # ── Datas formatadas ──
        def _fmt(raw):
            if not raw:
                return "—"
            try:
                return datetime.fromisoformat(
                    raw.replace("Z", "+00:00")
                ).strftime("%d/%m/%Y às %H:%M:%S UTC")
            except Exception:
                return raw

        decided_fmt = _fmt(cv.get("decided_at") or art_signed_raw)
        edit_signed_fmt = _fmt(edit_signed_raw)
        art_signed_fmt = _fmt(art_signed_raw)
        termo_versao = cv.get("termo_versao") or "v1"

        # ── Hash do documento ──
        doc_text = (cv.get("termo_html") or "").strip()
        digest_input = f"{doc_text}\n{convite_id}\n{edit_token}:{art_token}"
        doc_hash = hashlib.sha256(digest_input.encode("utf-8")).hexdigest()

        separador = "═" * 70

        # ── Bloco texto ──
        cert_txt = (
            f"\n\n{separador}\n"
            f"  CERTIFICADO DE ASSINATURAS DIGITAIS — GRAVAN\n"
            f"  Emitido em: {decided_fmt}\n"
            f"{separador}\n\n"
            f"  Tipo           : Termo de Agregação Musical\n"
            f"  Versão do Termo: {termo_versao}\n"
            f"  Convite ID     : {convite_id}\n"
            f"  Base legal     : MP 2.200-2/2001 · Lei 14.063/2020 · LGPD 13.709/2018\n\n"
            f"  SIGNATÁRIOS:\n\n"
            f"  [1] {edit_nome}\n"
            f"      Identificação : {edit_doc}\n"
            f"      E-mail        : {edit_email}\n"
            f"      Papel         : Editora Musical (Proponente)\n"
            f"      Data/Hora     : {edit_signed_fmt}\n"
            f"      IP (hash)     : {edit_ip}\n"
            f"      Tipo          : Assinatura eletrônica ao emitir o convite\n"
            f"      Token         : {edit_token}\n\n"
            f"  [2] {art_nome}\n"
            f"      Identificação : {art_cpf}\n"
            f"      E-mail        : {art_email}\n"
            f"      Papel         : Artista / Compositor(a) (Aderente)\n"
            f"      Data/Hora     : {art_signed_fmt}\n"
            f"      IP (hash)     : {art_ip}\n"
            f"      Tipo          : Assinatura eletrônica voluntária (aceite do termo)\n"
            f"      Token         : {art_token}\n\n"
            f"  INTEGRIDADE DO DOCUMENTO:\n"
            f"  Hash SHA-256   : {doc_hash}\n"
            f"  (Qualquer alteração posterior ao documento invalida este hash.)\n\n"
            f"  Este certificado faz parte integrante e inseparável do termo\n"
            f"  acima, tendo valor jurídico pleno conforme legislação vigente.\n"
            f"{separador}\n"
        )

        # ── Bloco HTML ──
        def _card(idx, nome, doc, email, papel, signed_fmt, ip_h, tipo, token):
            return (
                f"<div style='background:#fff;border:1px solid #e0e0e0;"
                f"border-radius:6px;padding:14px 18px;margin-bottom:12px;'>"
                f"<b>[{idx}] {nome}</b><br>"
                f"<span style='font-size:12px;color:#555;'>"
                f"<b>CPF/CNPJ:</b> {doc} &nbsp;|&nbsp; <b>E-mail:</b> {email}<br>"
                f"<b>Papel:</b> {papel}<br>"
                f"<b>Assinatura:</b> {tipo}<br>"
                f"<b>Data/Hora:</b> {signed_fmt}<br>"
                f"<b>IP (hash):</b> {ip_h}<br>"
                f"<b>Token:</b> <code style='font-size:11px;'>{token}</code>"
                f"</span></div>"
            )

        cert_html = (
            "<div style='margin-top:40px;border:2px solid #1a1a2e;border-radius:8px;"
            "padding:28px 32px;background:#f9f9ff;font-family:Georgia,serif;"
            "font-size:13px;line-height:1.8;color:#111;'>"
            "<div style='font-size:15px;font-weight:700;letter-spacing:1px;"
            "margin-bottom:16px;color:#1a1a2e;border-bottom:1px solid #ccc;"
            "padding-bottom:10px;'>CERTIFICADO DE ASSINATURAS DIGITAIS — GRAVAN</div>"
            f"<p><b>Tipo:</b> Termo de Agregação Musical<br>"
            f"<b>Versão do Termo:</b> {termo_versao}<br>"
            f"<b>Convite ID:</b> {convite_id}<br>"
            f"<b>Emitido em:</b> {decided_fmt}<br>"
            f"<b>Base legal:</b> MP 2.200-2/2001 · Lei 14.063/2020 · LGPD 13.709/2018</p>"
            "<hr style='margin:16px 0'><b>SIGNATÁRIOS:</b><br><br>"
        )
        cert_html += _card(1, edit_nome, edit_doc, edit_email,
                           "Editora Musical (Proponente)",
                           edit_signed_fmt, edit_ip,
                           "Eletrônica ao emitir o convite", edit_token)
        cert_html += _card(2, art_nome, art_cpf, art_email,
                           "Artista / Compositor(a) (Aderente)",
                           art_signed_fmt, art_ip,
                           "Voluntária (aceite do termo)", art_token)
        cert_html += (
            "<hr style='margin:16px 0'>"
            f"<p style='font-size:12px;'><b>Hash SHA-256 do documento:</b><br>"
            f"<code style='font-size:11px;word-break:break-all;'>{doc_hash}</code><br>"
            f"<i>Qualquer alteração posterior invalida este hash.</i></p>"
            "<p style='font-size:11px;color:#666;'>"
            "Este certificado faz parte integrante e inseparável do termo de agregação, "
            "tendo valor jurídico pleno conforme MP 2.200-2/2001 e Lei 14.063/2020.</p>"
            "</div>"
        )

        novo_html = (cv.get("termo_html") or "") + cert_html
        # Versão texto puro: usa o texto armazenado (gerado no aceite) e annexa
        # o bloco de certificado em plain-text; preserva qualidade de exibição no frontend.
        texto_base = cv.get("termo_text") or ""
        novo_text = texto_base + cert_txt
        agora = datetime.now(timezone.utc).isoformat()

        sb.table("agregado_convites").update({
            "termo_html":       novo_html,
            "termo_text":       novo_text,
            "certificado_html": cert_html,
            "certificado_hash": doc_hash,
            "certificado_at":   agora,
        }).eq("id", convite_id).execute()

        logger.info(
            "Certificado de agregação gerado para convite %s — hash: %s",
            convite_id, doc_hash,
        )
        return {"ok": True, "hash": doc_hash}

    except Exception as e:
        logger.exception(
            "Erro ao gerar certificado de agregação para convite %s: %s",
            convite_id, e,
        )
        return {"ok": False, "erro": str(e)}
