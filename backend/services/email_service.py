"""
Serviço de envio de e-mail.

Usa SMTP genérico configurado por variáveis de ambiente:
  SMTP_HOST       (ex.: smtp.resend.com, smtp.gmail.com, smtp.sendgrid.net)
  SMTP_PORT       (587 STARTTLS, 465 SSL)
  SMTP_USER       (usuário/api-key)
  SMTP_PASS       (senha/api-secret)
  SMTP_FROM       (ex.: 'Gravan <noreply@gravan>')
  SMTP_USE_SSL    ('1' para 465, vazio/0 para STARTTLS)

Fallback: se SMTP_HOST não estiver configurado, loga o e-mail e devolve True.
Isso permite testar localmente sem SMTP — você vê o OTP no console do backend.
"""
import os
import ssl
import smtplib
import logging
from email.message import EmailMessage
from email.utils import formataddr

log = logging.getLogger("gravan.email")


def _smtp_configured() -> bool:
    return bool(os.environ.get("SMTP_HOST") and os.environ.get("SMTP_FROM"))


def send_email(
    to: str,
    subject: str,
    html: str,
    text: str | None = None,
    attachments: list[dict] | None = None,
) -> bool:
    """Envia um e-mail. Retorna True se enviado (ou simulado em dev).

    attachments: lista de dicts com chaves:
        - data (bytes)     : conteúdo do arquivo
        - filename (str)   : nome do arquivo (ex.: 'contrato.pdf')
        - maintype (str)   : tipo MIME principal  (ex.: 'application')
        - subtype  (str)   : subtipo MIME         (ex.: 'pdf')
    """
    if not to:
        log.warning("send_email: destinatário vazio.")
        return False

    if not _smtp_configured():
        log.info("=" * 60)
        log.info("[DEV — SMTP não configurado] Simulando envio:")
        log.info("   PARA:    %s", to)
        log.info("   ASSUNTO: %s", subject)
        if attachments:
            log.info("   ANEXOS:  %s", [a.get("filename") for a in attachments])
        log.info("   TEXTO:")
        for ln in (text or html).splitlines():
            log.info("      %s", ln)
        log.info("=" * 60)
        return True

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = os.environ["SMTP_FROM"]
    msg["To"] = to
    msg.set_content(text or "Veja este e-mail em um cliente compatível com HTML.")
    msg.add_alternative(html, subtype="html")

    for att in (attachments or []):
        try:
            msg.add_attachment(
                att["data"],
                maintype=att.get("maintype", "application"),
                subtype=att.get("subtype", "octet-stream"),
                filename=att.get("filename", "anexo"),
            )
        except Exception as e:
            log.warning("Falha ao anexar %s: %s", att.get("filename"), e)

    host = os.environ["SMTP_HOST"]
    port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ.get("SMTP_USER", "")
    pwd  = os.environ.get("SMTP_PASS", "")
    use_ssl = os.environ.get("SMTP_USE_SSL", "").lower() in ("1", "true", "yes")

    try:
        ctx = ssl.create_default_context()
        if use_ssl:
            with smtplib.SMTP_SSL(host, port, context=ctx, timeout=15) as s:
                if user:
                    s.login(user, pwd)
                s.send_message(msg)
        else:
            with smtplib.SMTP(host, port, timeout=15) as s:
                s.ehlo()
                s.starttls(context=ctx)
                s.ehlo()
                if user:
                    s.login(user, pwd)
                s.send_message(msg)
        log.info("E-mail enviado para %s (assunto=%r)", to, subject)
        return True
    except Exception as e:
        log.error("Falha ao enviar e-mail para %s: %s", to, e)
        return False


# ─────────── Helpers de templates ───────────

def _wrap_html(title: str, body_html: str) -> str:
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>{title}</title></head>
<body style="font-family:-apple-system,Segoe UI,Roboto,sans-serif;background:#f6f6f7;margin:0;padding:24px;color:#111">
  <div style="max-width:560px;margin:0 auto;background:#fff;border-radius:14px;padding:32px;box-shadow:0 2px 12px rgba(0,0,0,.06)">
    <div style="font-weight:800;font-size:18px;color:#BE123C;margin-bottom:24px">Gravan</div>
    {body_html}
    <hr style="border:none;border-top:1px solid #eee;margin:28px 0">
    <p style="font-size:11px;color:#888;line-height:1.5">
      Este é um e-mail automático. Se você não solicitou, ignore esta mensagem.<br>
      Gravan &middot; Marketplace de composições musicais
    </p>
  </div>
</body></html>"""


def render_otp_email(nome: str, codigo: str, valor_brl: str, ip: str) -> tuple[str, str]:
    """Retorna (html, text) para o e-mail de código OTP de saque."""
    body = f"""
    <h2 style="margin:0 0 8px">Confirme sua solicitação de saque</h2>
    <p style="color:#444;font-size:14px">
      Olá {nome or 'compositor'}, recebemos um pedido de saque de
      <strong>{valor_brl}</strong> da sua wallet Gravan.
    </p>
    <p style="color:#444;font-size:14px">Use o código abaixo para confirmar — ele expira em <strong>10 minutos</strong>:</p>
    <div style="text-align:center;margin:24px 0;padding:18px;background:#FAFAFA;border:1px dashed #BE123C;border-radius:10px">
      <div style="font-size:36px;font-weight:800;letter-spacing:8px;color:#BE123C;font-family:'Courier New',monospace">{codigo}</div>
    </div>
    <p style="color:#666;font-size:12px">
      Solicitado a partir do IP <code>{ip}</code>.<br>
      <strong>Não foi você?</strong> Ignore este e-mail e troque sua senha imediatamente.
    </p>
    """
    text = (
        f"Gravan — Confirmação de saque\n\n"
        f"Valor: {valor_brl}\n"
        f"Código de confirmação (expira em 10 min): {codigo}\n\n"
        f"IP da solicitação: {ip}\n"
        f"Se não foi você, ignore este e-mail e troque sua senha."
    )
    return _wrap_html("Confirme seu saque", body), text


def render_saque_agendado_email(nome: str, valor_brl: str, libera_em: str,
                                cancel_url: str) -> tuple[str, str]:
    body = f"""
    <h2 style="margin:0 0 8px">Saque agendado para {libera_em}</h2>
    <p style="color:#444;font-size:14px">
      Olá {nome or 'compositor'}, seu saque de <strong>{valor_brl}</strong> foi
      <strong>confirmado</strong> e está agendado para liberação em
      <strong>{libera_em}</strong> (24 h de janela de segurança).
    </p>
    <p style="color:#444;font-size:14px">
      Se foi você, não precisa fazer nada — o dinheiro cai automaticamente na sua conta Stripe.
    </p>
    <div style="text-align:center;margin:28px 0">
      <a href="{cancel_url}" style="display:inline-block;padding:14px 28px;
         background:#fff;color:#BE123C;text-decoration:none;
         border:2px solid #BE123C;border-radius:10px;font-weight:700">
        🚫 Não fui eu — cancelar este saque
      </a>
    </div>
    <p style="color:#666;font-size:12px">
      O link acima é único, válido até a liberação. Cancelando, o valor volta integralmente para sua wallet.
    </p>
    """
    text = (
        f"Gravan — Saque agendado\n\n"
        f"Valor: {valor_brl}\n"
        f"Liberação: {libera_em}\n\n"
        f"Se NÃO foi você, cancele agora:\n{cancel_url}\n"
    )
    return _wrap_html("Saque agendado", body), text


def render_saque_pago_email(nome: str, valor_brl: str, transfer_id: str) -> tuple[str, str]:
    body = f"""
    <h2 style="margin:0 0 8px">✅ Saque enviado</h2>
    <p style="color:#444;font-size:14px">
      Olá {nome or 'compositor'}, seu saque de <strong>{valor_brl}</strong> foi
      enviado para sua conta Stripe.
    </p>
    <p style="color:#666;font-size:12px">
      Identificador Stripe: <code>{transfer_id}</code><br>
      O prazo de compensação bancária depende do seu banco (geralmente 1-3 dias úteis).
    </p>
    """
    return _wrap_html("Saque enviado", body), f"Saque {valor_brl} enviado. Stripe: {transfer_id}"


def render_oferta_editora_email(
    nome_editora: str, nome_obra: str, valor_brl: str,
    nome_comprador: str, deadline_str: str, link: str,
) -> tuple[str, str]:
    body = f"""
    <h2 style="margin:0 0 8px">Pedido de licenciamento de \"{nome_obra}\"</h2>
    <p style="color:#444;font-size:14px">
      Olá, equipe da <strong>{nome_editora}</strong>. Recebemos uma oferta de
      <strong>{valor_brl}</strong> de <strong>{nome_comprador}</strong> para licenciar a
      composição <strong>"{nome_obra}"</strong>, hoje sob seu contrato de edição.
    </p>
    <p style="color:#444;font-size:14px">
      O valor está retido em escrow pela Gravan. Para liberar a transação,
      vocês precisam <strong>cadastrar a editora</strong> na plataforma e assinar
      eletronicamente o contrato trilateral até:
    </p>
    <p style="text-align:center;font-size:16px;font-weight:700;margin:18px 0;color:#BE123C">
      ⏰ {deadline_str}
    </p>
    <div style="text-align:center;margin:24px 0">
      <a href="{link}" style="display:inline-block;padding:14px 28px;
         background:#BE123C;color:#fff;text-decoration:none;
         border-radius:10px;font-weight:700">
        Cadastrar editora e responder
      </a>
    </div>
    <p style="color:#666;font-size:12px">
      O prazo conta apenas horas úteis (segunda a sexta, 10h–18h, horário de
      Brasília, excluindo feriados nacionais). Caso o prazo expire sem resposta,
      o valor será integralmente estornado ao comprador.
    </p>
    """
    text = (
        f"Gravan — Pedido de licenciamento\n\n"
        f"Obra: {nome_obra}\nValor ofertado: {valor_brl}\nComprador: {nome_comprador}\n"
        f"Prazo: {deadline_str}\n\nResponda em: {link}\n"
    )
    return _wrap_html(f"Pedido de licenciamento — {nome_obra}", body), text


def render_oferta_reminder_email(
    nome_editora: str, nome_obra: str, valor_brl: str,
    horas_restantes: int, link: str,
) -> tuple[str, str]:
    body = f"""
    <h2 style="margin:0 0 8px">Faltam ~{horas_restantes}h úteis</h2>
    <p style="color:#444;font-size:14px">
      A oferta de <strong>{valor_brl}</strong> para a obra <strong>"{nome_obra}"</strong>
      ainda aguarda resposta da <strong>{nome_editora}</strong>.
    </p>
    <p style="color:#B91C1C;font-size:14px">
      Se o prazo expirar, o valor é estornado ao comprador automaticamente.
    </p>
    <div style="text-align:center;margin:24px 0">
      <a href="{link}" style="display:inline-block;padding:14px 28px;
         background:#BE123C;color:#fff;text-decoration:none;
         border-radius:10px;font-weight:700">
        Responder agora
      </a>
    </div>
    """
    text = (
        f"Gravan — Lembrete de oferta\n\n"
        f"Obra: {nome_obra}\nValor: {valor_brl}\n"
        f"Faltam ~{horas_restantes}h úteis. Responda em: {link}\n"
    )
    return _wrap_html(f"Lembrete: {nome_obra}", body), text


def render_oferta_expirada_comprador_email(
    nome_comprador: str, nome_obra: str, valor_brl: str,
) -> tuple[str, str]:
    body = f"""
    <h2 style="margin:0 0 8px">Oferta expirada e valor estornado</h2>
    <p style="color:#444;font-size:14px">
      Olá {nome_comprador}, a editora detentora dos direitos de edição da obra
      <strong>"{nome_obra}"</strong> não respondeu dentro do prazo de 72 horas úteis.
    </p>
    <p style="color:#444;font-size:14px">
      O valor de <strong>{valor_brl}</strong> foi <strong>integralmente estornado</strong>
      para o seu cartão. O prazo de compensação depende da operadora (geralmente 5 a 10 dias úteis).
    </p>
    """
    return _wrap_html("Oferta expirada", body), \
        f"Gravan — Oferta expirada\nObra: {nome_obra}\nValor estornado: {valor_brl}"


def render_oferta_expirada_editora_email(nome_editora: str, nome_obra: str) -> tuple[str, str]:
    body = f"""
    <h2 style="margin:0 0 8px">Prazo da oferta expirado</h2>
    <p style="color:#444;font-size:14px">
      A oferta para a obra <strong>"{nome_obra}"</strong> direcionada à
      <strong>{nome_editora}</strong> não foi respondida dentro de 72 horas úteis e
      foi cancelada. O valor foi estornado ao comprador.
    </p>
    <p style="color:#666;font-size:12px">
      Se quiser receber novas ofertas pela Gravan, mantenha seu cadastro atualizado.
    </p>
    """
    return _wrap_html("Prazo expirado", body), \
        f"Gravan — Prazo da oferta para \"{nome_obra}\" expirou."


def render_oferta_concluida_email(nome_comprador: str, nome_obra: str, valor_brl: str) -> tuple[str, str]:
    body = f"""
    <h2 style="margin:0 0 8px">✅ Licença concluída</h2>
    <p style="color:#444;font-size:14px">
      Olá {nome_comprador}, todas as partes assinaram o contrato trilateral
      da obra <strong>"{nome_obra}"</strong>. O valor de <strong>{valor_brl}</strong>
      foi capturado e a licença está formalmente ativa.
    </p>
    <p style="color:#666;font-size:12px">
      Você pode acessar o contrato e o áudio na sua área de Compras na Gravan.
    </p>
    """
    return _wrap_html("Licença concluída", body), \
        f"Gravan — Licença de \"{nome_obra}\" concluída ({valor_brl})."


def render_saque_cancelado_email(nome: str, valor_brl: str, motivo: str) -> tuple[str, str]:
    body = f"""
    <h2 style="margin:0 0 8px">Saque cancelado</h2>
    <p style="color:#444;font-size:14px">
      Olá {nome or 'compositor'}, o saque de <strong>{valor_brl}</strong> foi cancelado.
      O valor voltou integralmente para sua wallet.
    </p>
    <p style="color:#666;font-size:13px"><strong>Motivo:</strong> {motivo}</p>
    <p style="color:#B91C1C;font-size:13px">
      Se você NÃO solicitou esse saque originalmente, recomendamos:
    </p>
    <ul style="color:#444;font-size:13px">
      <li>Trocar sua senha imediatamente</li>
      <li>Verificar dispositivos conectados na sua conta</li>
      <li>Entrar em contato com nosso suporte</li>
    </ul>
    """
    return _wrap_html("Saque cancelado", body), f"Saque {valor_brl} cancelado. Motivo: {motivo}"


def render_licenciamento_concluido_email(
    nome: str,
    papel: str,
    nome_obra: str,
    valor_brl: str,
    contract_id: str,
    frontend_url: str,
) -> tuple[str, str]:
    """E-mail enviado a TODAS as partes quando o contrato de licenciamento é concluído.
    Inclui o PDF como anexo — veja send_email(attachments=...).

    papel: 'autor' | 'coautor' | 'interprete' | 'editora'
    """
    papel_label = {
        "autor":      "compositor(a) titular",
        "coautor":    "coautor(a)",
        "interprete": "intérprete/licenciado(a)",
        "editora":    "editora",
    }.get(papel, "parte")

    link = f"{frontend_url.rstrip('/')}/contratos/licenciamento/{contract_id}"

    body = f"""
    <h2 style="margin:0 0 8px">Contrato de licenciamento concluído</h2>
    <p style="color:#444;font-size:14px">
      Olá <strong>{nome or papel_label}</strong>, todas as partes assinaram o
      <strong>Contrato de Autorização para Gravação e Exploração</strong> da obra
      <strong>"{nome_obra}"</strong>.
    </p>
    <p style="color:#444;font-size:14px">
      O contrato assinado está em anexo neste e-mail (PDF). Guarde este arquivo — ele é
      sua prova legal da licença.
    </p>
    <table style="width:100%;margin:16px 0;border-collapse:collapse">
      <tr>
        <td style="padding:8px 12px;background:#F9FAFB;border:1px solid #E5E7EB;font-size:12px;color:#6B7280">Obra</td>
        <td style="padding:8px 12px;background:#F9FAFB;border:1px solid #E5E7EB;font-size:13px;font-weight:700">{nome_obra}</td>
      </tr>
      <tr>
        <td style="padding:8px 12px;border:1px solid #E5E7EB;font-size:12px;color:#6B7280">Valor do licenciamento</td>
        <td style="padding:8px 12px;border:1px solid #E5E7EB;font-size:13px;font-weight:700;color:#BE123C">{valor_brl}</td>
      </tr>
      <tr>
        <td style="padding:8px 12px;background:#F9FAFB;border:1px solid #E5E7EB;font-size:12px;color:#6B7280">Seu papel</td>
        <td style="padding:8px 12px;background:#F9FAFB;border:1px solid #E5E7EB;font-size:13px">{papel_label.capitalize()}</td>
      </tr>
    </table>
    <div style="text-align:center;margin:24px 0">
      <a href="{link}" style="display:inline-block;padding:14px 28px;
         background:#BE123C;color:#fff;text-decoration:none;
         border-radius:10px;font-weight:700">
        Ver contrato na plataforma
      </a>
    </div>
    <p style="color:#888;font-size:11px">
      Validade legal: este contrato foi assinado eletronicamente nos termos da
      MP 2.200-2/2001 e da Lei 14.063/2020. O hash SHA-256 de integridade consta
      no documento. Guarde o PDF para seus registros.
    </p>
    """
    text = (
        f"Gravan — Contrato de licenciamento concluído\n\n"
        f"Olá {nome or papel_label},\n\n"
        f"Todas as partes assinaram o contrato de licenciamento da obra "
        f"\"{nome_obra}\" (valor: {valor_brl}).\n\n"
        f"O contrato assinado está em anexo neste e-mail (PDF).\n\n"
        f"Acesse também em: {link}\n"
    )
    return _wrap_html(f"Contrato concluído — {nome_obra}", body), text


def render_rescisao_exclusividade_email(
    nome_destinatario: str,
    papel: str,
    nome_obra: str,
    nome_comprador: str,
    data_venda_brt: str,
) -> tuple[str, str]:
    """
    E-mail formal de rescisão dos demais contratos de licenciamento da obra
    em razão de venda de exclusividade. Enviado ao compositor, coautores e à
    editora (agregada ou terceira).

    `papel`: 'compositor' | 'coautor' | 'editora' — usado só pra personalizar o tom.
    """
    saudacao = {
        "compositor": "compositor(a)",
        "coautor":    "coautor(a)",
        "editora":    "editora",
    }.get(papel, "parte interessada")

    body = f"""
    <h2 style="margin:0 0 8px">Comunicação formal de rescisão</h2>
    <p style="color:#444;font-size:14px">
      Prezado(a) {nome_destinatario or saudacao},
    </p>
    <p style="color:#444;font-size:14px">
      Comunicamos formalmente, na qualidade de plataforma intermediária dos
      licenciamentos da obra <strong>"{nome_obra}"</strong>, a
      <strong>rescisão</strong> de todos os contratos de licenciamento até então
      vigentes referentes a esta obra.
    </p>
    <div style="margin:16px 0;padding:14px 16px;background:#FEF2F2;border-left:4px solid #BE123C;border-radius:6px">
      <p style="margin:0;color:#7F1D1D;font-size:13px">
        <strong>Motivo:</strong> venda da licença de <strong>EXCLUSIVIDADE</strong> da obra
        a {nome_comprador or 'novo licenciado'}, formalizada em {data_venda_brt}
        por meio da plataforma GRAVAN.
      </p>
    </div>
    <p style="color:#444;font-size:14px">
      Em conformidade com a CLÁUSULA 3 (bilateral) / CLÁUSULA 5 (trilateral) dos
      contratos vigentes — Parágrafo Primeiro (Rescisão) — esta comunicação
      observa o prazo de <strong>30 (trinta) dias</strong> de antecedência. As
      explorações comerciais já realizadas, e aquelas realizadas até o término
      desse prazo, permanecem válidas e definitivas.
    </p>
    <p style="color:#444;font-size:14px">
      A partir desta data, a obra passa a constar como
      <strong>indisponível para novos licenciamentos</strong> no catálogo da
      GRAVAN, pelo período de exclusividade contratado (5 anos).
    </p>
    <p style="color:#666;font-size:12px;margin-top:24px">
      Em caso de dúvidas, responda a este e-mail ou entre em contato com o
      suporte da Gravan.
    </p>
    """
    text = (
        f"Gravan — Comunicação formal de rescisão\n\n"
        f"Prezado(a) {nome_destinatario or saudacao},\n\n"
        f"Comunicamos formalmente a rescisão dos contratos de licenciamento da "
        f"obra \"{nome_obra}\".\n\n"
        f"Motivo: venda da licença de EXCLUSIVIDADE a {nome_comprador or 'novo licenciado'}, "
        f"formalizada em {data_venda_brt} pela plataforma GRAVAN.\n\n"
        f"Esta comunicação observa o prazo de 30 dias de antecedência previsto na "
        f"CLÁUSULA 3/5 — Parágrafo Primeiro dos contratos. As explorações já "
        f"realizadas e as realizadas até o término desse prazo permanecem válidas.\n\n"
        f"A obra passa a constar como indisponível para novos licenciamentos pelo "
        f"período de exclusividade contratado (5 anos).\n"
    )
    return _wrap_html(f"Rescisão — \"{nome_obra}\"", body), text
