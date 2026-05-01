"""
Serviço de envio de e-mail.

Usa SMTP genérico configurado por variáveis de ambiente:
  SMTP_HOST       (ex.: smtp.resend.com, smtp.gmail.com, smtp.sendgrid.net)
  SMTP_PORT       (587 STARTTLS, 465 SSL)
  SMTP_USER       (usuário/api-key)
  SMTP_PASS       (senha/api-secret)
  SMTP_FROM       (ex.: 'Gravan <noreply@gravan.com.br>')
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


# ─────────── Base do template ───────────

def _wrap_html(title: str, body_html: str, accent: str = "#BE123C") -> str:
    """
    Wrapper HTML completo para todos os e-mails da Gravan.
    accent: cor da barra superior — use variações para identificar o tipo de e-mail:
      #BE123C  vermelho  → padrão / ações importantes
      #16a34a  verde     → sucesso / confirmação
      #d97706  âmbar     → atenção / prazo
      #1d4ed8  azul      → informativo
    """
    return f"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <!--[if mso]><noscript><xml><o:OfficeDocumentSettings><o:PixelsPerInch>96</o:PixelsPerInch></o:OfficeDocumentSettings></xml></noscript><![endif]-->
</head>
<body style="margin:0;padding:0;background-color:#F4F4F5;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;-webkit-text-size-adjust:100%;-ms-text-size-adjust:100%;">

  <table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="background-color:#F4F4F5;padding:32px 16px;">
    <tr>
      <td align="center">
        <table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="max-width:580px;">

          <!-- HEADER -->
          <tr>
            <td align="center" style="padding-bottom:20px;">
              <table role="presentation" cellpadding="0" cellspacing="0" width="100%"
                     style="background-color:#09090B;border-radius:14px 14px 0 0;overflow:hidden;">
                <tr>
                  <td style="height:4px;background-color:{accent};font-size:0;line-height:0;">&nbsp;</td>
                </tr>
                <tr>
                  <td style="padding:24px 32px;">
                    <table role="presentation" cellpadding="0" cellspacing="0" width="100%">
                      <tr>
                        <td>
                          <span style="font-size:20px;font-weight:800;color:#FFFFFF;letter-spacing:-0.5px;">
                            &#9679;&nbsp;gravan
                          </span>
                        </td>
                        <td align="right">
                          <span style="font-size:11px;color:#71717A;letter-spacing:0.08em;text-transform:uppercase;">
                            Marketplace musical
                          </span>
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- BODY -->
          <tr>
            <td style="padding-bottom:20px;">
              <table role="presentation" cellpadding="0" cellspacing="0" width="100%"
                     style="background-color:#FFFFFF;border-radius:0 0 14px 14px;overflow:hidden;">
                <tr>
                  <td style="padding:32px 32px 24px;">
                    {body_html}
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- FOOTER -->
          <tr>
            <td align="center" style="padding-bottom:32px;">
              <p style="margin:0 0 8px;font-size:12px;color:#71717A;text-align:center;">
                Este é um e-mail automático enviado pela Gravan.
              </p>
              <p style="margin:0 0 8px;font-size:12px;color:#71717A;text-align:center;">
                <a href="https://www.gravan.com.br" style="color:#BE123C;text-decoration:none;">www.gravan.com.br</a>
                &nbsp;&middot;&nbsp;
                <a href="mailto:contato@gravan.com.br" style="color:#BE123C;text-decoration:none;">contato@gravan.com.br</a>
              </p>
              <p style="margin:0;font-size:11px;color:#A1A1AA;text-align:center;">
                &copy; 2025 Gravan &middot; Marketplace de composições musicais
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>

</body>
</html>"""


def _btn(label: str, url: str, color: str = "#BE123C") -> str:
    """Botão CTA padrão para e-mails."""
    return f"""
<table role="presentation" cellpadding="0" cellspacing="0" style="margin:24px auto;">
  <tr>
    <td align="center" style="background-color:{color};border-radius:10px;">
      <a href="{url}"
         style="display:inline-block;padding:14px 32px;font-size:14px;font-weight:700;
                color:#FFFFFF;text-decoration:none;letter-spacing:0.02em;">
        {label}
      </a>
    </td>
  </tr>
</table>"""


def _divider() -> str:
    return '<table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="margin:20px 0;"><tr><td style="border-top:1px solid #E4E4E7;font-size:0;line-height:0;">&nbsp;</td></tr></table>'


def _info_row(label: str, value: str) -> str:
    return f"""
<tr>
  <td style="padding:10px 14px;font-size:12px;color:#71717A;background-color:#FAFAFA;
             border:1px solid #E4E4E7;border-bottom:none;white-space:nowrap;width:40%;">{label}</td>
  <td style="padding:10px 14px;font-size:13px;font-weight:600;color:#09090B;
             background-color:#FAFAFA;border:1px solid #E4E4E7;border-bottom:none;">{value}</td>
</tr>"""


def _info_table(*rows_html: str) -> str:
    rows = "".join(rows_html)
    last = rows.rfind('border-bottom:none;')
    fixed = rows[:last] + rows[last:].replace('border-bottom:none;', '', 1)
    return f'<table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="margin:20px 0;border-collapse:collapse;">{fixed}</table>'


def _alert(text: str, color: str = "#FEF3C7", border: str = "#D97706", txt: str = "#78350F") -> str:
    return f"""
<table role="presentation" cellpadding="0" cellspacing="0" width="100%"
       style="margin:16px 0;background-color:{color};border-left:4px solid {border};border-radius:0 8px 8px 0;">
  <tr>
    <td style="padding:12px 16px;font-size:13px;color:{txt};line-height:1.5;">
      {text}
    </td>
  </tr>
</table>"""


# ─────────── Templates ───────────

def render_otp_email(nome: str, codigo: str, valor_brl: str, ip: str) -> tuple[str, str]:
    """E-mail de código OTP para confirmação de saque."""
    body = f"""
<h2 style="margin:0 0 6px;font-size:22px;font-weight:800;color:#09090B;">
  Confirme seu saque
</h2>
<p style="margin:0 0 20px;font-size:14px;color:#52525B;line-height:1.6;">
  Olá, <strong>{nome or 'compositor'}</strong>. Recebemos uma solicitação de saque de
  <strong style="color:#09090B;">{valor_brl}</strong> da sua carteira Gravan.
</p>

<p style="margin:0 0 8px;font-size:13px;color:#52525B;">
  Use o código abaixo para confirmar. Ele expira em <strong>10 minutos</strong>:
</p>

<table role="presentation" cellpadding="0" cellspacing="0" width="100%"
       style="margin:20px 0;background-color:#09090B;border-radius:12px;">
  <tr>
    <td align="center" style="padding:28px 20px;">
      <span style="font-size:42px;font-weight:900;letter-spacing:12px;color:#FFFFFF;
                   font-family:'Courier New',Courier,monospace;">{codigo}</span>
      <br>
      <span style="font-size:11px;color:#71717A;letter-spacing:0.08em;text-transform:uppercase;margin-top:8px;display:block;">
        Código de confirmação &middot; válido por 10 minutos
      </span>
    </td>
  </tr>
</table>

{_info_table(
    _info_row("Valor do saque", valor_brl),
    _info_row("IP da solicitação", ip),
)}

{_alert(
    "<strong>Não foi você?</strong> Ignore este e-mail e troque sua senha imediatamente em Configurações.",
    "#FEF2F2", "#BE123C", "#7F1D1D"
)}

<p style="margin:16px 0 0;font-size:12px;color:#A1A1AA;line-height:1.5;">
  Por segurança, nunca compartilhe este código com ninguém. A Gravan jamais solicitará
  seu código por telefone ou chat.
</p>
"""
    text = (
        f"Gravan — Confirmação de saque\n\n"
        f"Valor: {valor_brl}\n"
        f"Código de confirmação (expira em 10 min): {codigo}\n\n"
        f"IP da solicitação: {ip}\n"
        f"Se não foi você, ignore este e-mail e troque sua senha."
    )
    return _wrap_html("Confirme seu saque — Gravan", body, accent="#BE123C"), text


def render_saque_agendado_email(nome: str, valor_brl: str, libera_em: str,
                                cancel_url: str) -> tuple[str, str]:
    body = f"""
<h2 style="margin:0 0 6px;font-size:22px;font-weight:800;color:#09090B;">
  Saque agendado ✓
</h2>
<p style="margin:0 0 20px;font-size:14px;color:#52525B;line-height:1.6;">
  Olá, <strong>{nome or 'compositor'}</strong>. Seu saque foi confirmado e está
  na janela de segurança de 24 horas antes de ser processado.
</p>

{_info_table(
    _info_row("Valor", valor_brl),
    _info_row("Liberação prevista", libera_em),
    _info_row("Status", "Aguardando janela de 24h"),
)}

<p style="margin:20px 0 8px;font-size:14px;color:#52525B;line-height:1.6;">
  Se foi você quem solicitou, <strong>não precisa fazer nada</strong> — o valor
  será transferido automaticamente para sua conta Stripe na data acima.
</p>

{_divider()}

<p style="margin:0 0 6px;font-size:14px;font-weight:700;color:#7F1D1D;">
  Não reconhece esse saque?
</p>
<p style="margin:0 0 16px;font-size:13px;color:#52525B;line-height:1.5;">
  Cancele imediatamente. O valor volta integralmente para sua carteira.
</p>

{_btn("Cancelar este saque", cancel_url, "#BE123C")}

<p style="margin:0;font-size:11px;color:#A1A1AA;text-align:center;line-height:1.5;">
  Este link de cancelamento é de uso único e expira na data de liberação.
</p>
"""
    text = (
        f"Gravan — Saque agendado\n\n"
        f"Valor: {valor_brl}\n"
        f"Liberação: {libera_em}\n\n"
        f"Se NÃO foi você, cancele agora:\n{cancel_url}\n"
    )
    return _wrap_html("Saque agendado — Gravan", body, accent="#d97706"), text


def render_saque_pago_email(nome: str, valor_brl: str, transfer_id: str) -> tuple[str, str]:
    body = f"""
<table role="presentation" cellpadding="0" cellspacing="0" width="100%"
       style="margin:0 0 20px;">
  <tr>
    <td align="center">
      <div style="width:56px;height:56px;background-color:#DCFCE7;border-radius:50%;
                  line-height:56px;text-align:center;font-size:26px;margin:0 auto 12px;">✅</div>
      <h2 style="margin:0 0 6px;font-size:22px;font-weight:800;color:#09090B;">
        Saque enviado com sucesso
      </h2>
      <p style="margin:0;font-size:14px;color:#52525B;">
        Olá, <strong>{nome or 'compositor'}</strong>. Seu saque foi processado e está a caminho.
      </p>
    </td>
  </tr>
</table>

{_info_table(
    _info_row("Valor transferido", valor_brl),
    _info_row("ID Stripe", transfer_id),
    _info_row("Prazo de compensação", "1 a 3 dias úteis (depende do banco)"),
)}

{_alert(
    "O dinheiro aparecerá na sua conta bancária vinculada ao Stripe dentro do prazo acima.",
    "#F0FDF4", "#16a34a", "#14532D"
)}
"""
    text = (
        f"Gravan — Saque enviado\n\n"
        f"Valor: {valor_brl}\n"
        f"ID Stripe: {transfer_id}\n"
        f"Prazo de compensação: 1 a 3 dias úteis."
    )
    return _wrap_html("Saque enviado — Gravan", body, accent="#16a34a"), text


def render_saque_cancelado_email(nome: str, valor_brl: str, motivo: str) -> tuple[str, str]:
    _alerta = (
        "<strong>N\u00e3o reconhece esse cancelamento?</strong> Isso pode indicar acesso n\u00e3o autorizado. Recomendamos:<br>"
        "&bull; Trocar sua senha imediatamente<br>"
        "&bull; Verificar os dispositivos conectados \u00e0 sua conta<br>"
        '&bull; Entrar em contato: <a href="mailto:contato@gravan.com.br" style="color:#7F1D1D;">contato@gravan.com.br</a>'
    )
    _tabela = _info_table(_info_row("Valor estornado", valor_brl), _info_row("Motivo", motivo))
    _aviso  = _alert(_alerta, "#FEF2F2", "#BE123C", "#7F1D1D")
    body = f"""
<h2 style="margin:0 0 6px;font-size:22px;font-weight:800;color:#09090B;">
  Saque cancelado
</h2>
<p style="margin:0 0 20px;font-size:14px;color:#52525B;line-height:1.6;">
  Ol\u00e1, <strong>{nome or 'compositor'}</strong>. Seu saque foi cancelado e o valor
  foi devolvido integralmente \u00e0 sua carteira Gravan.
</p>
{_tabela}
{_aviso}
"""
    text = (
        f"Gravan — Saque cancelado\n\n"
        f"Valor estornado: {valor_brl}\n"
        f"Motivo: {motivo}\n\n"
        f"Se não reconhece, troque sua senha e entre em contato: contato@gravan.com.br"
    )
    return _wrap_html("Saque cancelado — Gravan", body, accent="#BE123C"), text


def render_oferta_editora_email(
    nome_editora: str, nome_obra: str, valor_brl: str,
    nome_comprador: str, deadline_str: str, link: str,
) -> tuple[str, str]:
    body = f"""
<h2 style="margin:0 0 6px;font-size:22px;font-weight:800;color:#09090B;">
  Nova oferta de licenciamento
</h2>
<p style="margin:0 0 20px;font-size:14px;color:#52525B;line-height:1.6;">
  Olá, equipe da <strong>{nome_editora}</strong>! Vocês receberam uma oferta de
  licenciamento para uma obra do catálogo.
</p>

{_info_table(
    _info_row("Obra", nome_obra),
    _info_row("Valor ofertado", valor_brl),
    _info_row("Comprador", nome_comprador),
    _info_row("Prazo para resposta", deadline_str),
)}

<p style="margin:20px 0 8px;font-size:14px;color:#52525B;line-height:1.6;">
  O valor está retido em <em>escrow</em> pela Gravan. Para liberar a transação,
  a editora precisa <strong>cadastrar-se na plataforma</strong> e assinar
  eletronicamente o contrato trilateral antes do prazo.
</p>

{_alert(
    f"<strong>Atenção:</strong> o prazo conta apenas em horas úteis (seg–sex, 10h–18h, horário de Brasília, excluindo feriados nacionais). Se o prazo expirar sem resposta, o valor é estornado integralmente ao comprador.",
    "#FEF3C7", "#D97706", "#78350F"
)}

{_btn("Cadastrar editora e responder", link, "#BE123C")}
"""
    text = (
        f"Gravan — Pedido de licenciamento\n\n"
        f"Obra: {nome_obra}\nValor ofertado: {valor_brl}\nComprador: {nome_comprador}\n"
        f"Prazo: {deadline_str}\n\nResponda em: {link}\n"
    )
    return _wrap_html(f"Nova oferta — {nome_obra} — Gravan", body, accent="#d97706"), text


def render_oferta_reminder_email(
    nome_editora: str, nome_obra: str, valor_brl: str,
    horas_restantes: int, link: str,
) -> tuple[str, str]:
    body = f"""
<h2 style="margin:0 0 6px;font-size:22px;font-weight:800;color:#09090B;">
  Lembrete: oferta prestes a expirar
</h2>
<p style="margin:0 0 20px;font-size:14px;color:#52525B;line-height:1.6;">
  Olá, <strong>{nome_editora}</strong>. A oferta de licenciamento da obra
  <strong>"{nome_obra}"</strong> ainda aguarda resposta.
</p>

{_info_table(
    _info_row("Obra", nome_obra),
    _info_row("Valor", valor_brl),
    _info_row("Horas restantes (úteis)", f"~{horas_restantes}h"),
)}

{_alert(
    "<strong>Atenção:</strong> se o prazo expirar sem resposta, o valor será integralmente estornado ao comprador e a oferta será cancelada automaticamente.",
    "#FEF2F2", "#BE123C", "#7F1D1D"
)}

{_btn("Responder agora", link, "#BE123C")}
"""
    text = (
        f"Gravan — Lembrete de oferta\n\n"
        f"Obra: {nome_obra}\nValor: {valor_brl}\n"
        f"Faltam ~{horas_restantes}h úteis. Responda em: {link}\n"
    )
    return _wrap_html(f"Lembrete: {nome_obra} — Gravan", body, accent="#BE123C"), text


def render_oferta_expirada_comprador_email(
    nome_comprador: str, nome_obra: str, valor_brl: str,
) -> tuple[str, str]:
    body = f"""
<h2 style="margin:0 0 6px;font-size:22px;font-weight:800;color:#09090B;">
  Oferta expirada — valor estornado
</h2>
<p style="margin:0 0 20px;font-size:14px;color:#52525B;line-height:1.6;">
  Olá, <strong>{nome_comprador}</strong>. A editora detentora dos direitos de edição
  da obra <strong>"{nome_obra}"</strong> não respondeu dentro do prazo de 72 horas úteis.
</p>

{_info_table(
    _info_row("Obra", nome_obra),
    _info_row("Valor estornado", valor_brl),
    _info_row("Prazo de compensação", "5 a 10 dias úteis (depende da operadora)"),
)}

{_alert(
    "O valor foi <strong>integralmente estornado</strong> para o seu cartão de crédito. "
    "Você pode explorar outras obras disponíveis no catálogo da Gravan.",
    "#F0FDF4", "#16a34a", "#14532D"
)}

{_btn("Explorar catálogo", "https://www.gravan.com.br/descoberta", "#09090B")}
"""
    text = (
        f"Gravan — Oferta expirada\n\n"
        f"Obra: {nome_obra}\nValor estornado: {valor_brl}\n"
        f"Prazo de compensação: 5 a 10 dias úteis."
    )
    return _wrap_html("Oferta expirada — Gravan", body, accent="#d97706"), text


def render_oferta_expirada_editora_email(nome_editora: str, nome_obra: str) -> tuple[str, str]:
    body = f"""
<h2 style="margin:0 0 6px;font-size:22px;font-weight:800;color:#09090B;">
  Prazo expirado
</h2>
<p style="margin:0 0 20px;font-size:14px;color:#52525B;line-height:1.6;">
  Olá, <strong>{nome_editora}</strong>. A oferta de licenciamento da obra
  <strong>"{nome_obra}"</strong> expirou sem resposta e foi automaticamente cancelada.
</p>

{_alert(
    "O valor foi integralmente estornado ao comprador. Para continuar recebendo ofertas pela Gravan, mantenha seu cadastro atualizado e responda dentro dos prazos.",
    "#FEF3C7", "#D97706", "#78350F"
)}
"""
    text = (
        f"Gravan — Prazo da oferta para \"{nome_obra}\" expirou.\n\n"
        f"O valor foi estornado ao comprador. Mantenha seu cadastro atualizado."
    )
    return _wrap_html("Prazo expirado — Gravan", body, accent="#d97706"), text


def render_oferta_concluida_email(nome_comprador: str, nome_obra: str, valor_brl: str) -> tuple[str, str]:
    body = f"""
<table role="presentation" cellpadding="0" cellspacing="0" width="100%"
       style="margin:0 0 20px;">
  <tr>
    <td align="center">
      <div style="width:56px;height:56px;background-color:#DCFCE7;border-radius:50%;
                  line-height:56px;text-align:center;font-size:26px;margin:0 auto 12px;">🎵</div>
      <h2 style="margin:0 0 6px;font-size:22px;font-weight:800;color:#09090B;">
        Licença concluída!
      </h2>
      <p style="margin:0;font-size:14px;color:#52525B;">
        Olá, <strong>{nome_comprador}</strong>. Todas as partes assinaram o contrato.
        A licença está formalmente ativa.
      </p>
    </td>
  </tr>
</table>

{_info_table(
    _info_row("Obra licenciada", nome_obra),
    _info_row("Valor pago", valor_brl),
    _info_row("Status", "Contrato assinado e ativo"),
)}

{_alert(
    "Você pode acessar o contrato e fazer o download do áudio na sua área de <strong>Compras</strong> na Gravan.",
    "#F0FDF4", "#16a34a", "#14532D"
)}

{_btn("Acessar minhas compras", "https://www.gravan.com.br/compras", "#16a34a")}
"""
    text = (
        f"Gravan — Licença concluída\n\n"
        f"Obra: {nome_obra}\nValor: {valor_brl}\n"
        f"Acesse seus contratos em: https://www.gravan.com.br/compras"
    )
    return _wrap_html(f"Licença concluída — {nome_obra} — Gravan", body, accent="#16a34a"), text


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
<h2 style="margin:0 0 6px;font-size:22px;font-weight:800;color:#09090B;">
  Contrato de licenciamento concluído
</h2>
<p style="margin:0 0 20px;font-size:14px;color:#52525B;line-height:1.6;">
  Olá, <strong>{nome or papel_label}</strong>. Todas as partes assinaram o
  <strong>Contrato de Autorização para Gravação e Exploração</strong> da obra abaixo.
  O contrato assinado está em <strong>anexo neste e-mail (PDF)</strong>.
</p>

{_info_table(
    _info_row("Obra", nome_obra),
    _info_row("Valor do licenciamento", valor_brl),
    _info_row("Seu papel", papel_label.capitalize()),
    _info_row("ID do contrato", contract_id),
)}

{_alert(
    "Guarde o PDF anexo — ele é sua prova legal da licença, assinado eletronicamente nos termos da MP 2.200-2/2001 e da Lei 14.063/2020.",
    "#EFF6FF", "#1d4ed8", "#1e3a8a"
)}

{_btn("Ver contrato na plataforma", link, "#09090B")}

<p style="margin:16px 0 0;font-size:11px;color:#A1A1AA;text-align:center;line-height:1.5;">
  O hash SHA-256 de integridade do documento consta no próprio PDF.
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
    return _wrap_html(f"Contrato concluído — {nome_obra} — Gravan", body, accent="#16a34a"), text


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

    `papel`: 'compositor' | 'coautor' | 'editora'
    """
    saudacao = {
        "compositor": "compositor(a)",
        "coautor":    "coautor(a)",
        "editora":    "editora",
    }.get(papel, "parte interessada")

    body = f"""
<h2 style="margin:0 0 6px;font-size:22px;font-weight:800;color:#09090B;">
  Comunicação formal de rescisão
</h2>
<p style="margin:0 0 20px;font-size:14px;color:#52525B;line-height:1.6;">
  Prezado(a) <strong>{nome_destinatario or saudacao}</strong>,
</p>
<p style="margin:0 0 20px;font-size:14px;color:#52525B;line-height:1.6;">
  Comunicamos formalmente, na qualidade de plataforma intermediária, a
  <strong>rescisão de todos os contratos de licenciamento</strong> vigentes
  referentes à obra abaixo.
</p>

{_info_table(
    _info_row("Obra", nome_obra),
    _info_row("Motivo", "Venda de licença de exclusividade"),
    _info_row("Novo licenciado exclusivo", nome_comprador or "—"),
    _info_row("Data da venda", data_venda_brt),
    _info_row("Período de exclusividade", "5 anos a partir da data da venda"),
)}

{_alert(
    "<strong>Prazo de aviso:</strong> esta comunicação observa os 30 (trinta) dias de antecedência previstos na Cláusula 3 (bilateral) / Cláusula 5 (trilateral) — Parágrafo Primeiro dos contratos vigentes. "
    "As explorações já realizadas e as realizadas até o término desse prazo permanecem <strong>válidas e definitivas</strong>.",
    "#FEF3C7", "#D97706", "#78350F"
)}

<p style="margin:16px 0 0;font-size:13px;color:#52525B;line-height:1.6;">
  A partir desta data, a obra consta como <strong>indisponível para novos licenciamentos</strong>
  no catálogo da Gravan pelo período de exclusividade contratado.
</p>

{_divider()}

<p style="margin:0;font-size:12px;color:#A1A1AA;line-height:1.5;">
  Dúvidas? Responda este e-mail ou escreva para
  <a href="mailto:contato@gravan.com.br" style="color:#BE123C;">contato@gravan.com.br</a>.
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
        f"Cláusula 3/5 — Parágrafo Primeiro dos contratos. As explorações já "
        f"realizadas e as realizadas até o término desse prazo permanecem válidas.\n\n"
        f"A obra passa a constar como indisponível para novos licenciamentos pelo "
        f"período de exclusividade contratado (5 anos).\n"
    )
    return _wrap_html(f"Rescisão — \"{nome_obra}\" — Gravan", body, accent="#BE123C"), text



def render_oferta_notificacao_compositor_email(
    nome: str, nome_obra: str, valor_brl: str,
    nome_comprador: str, deadline_str: str,
) -> tuple[str, str]:
    """Notificação informativa ao compositor/coautor quando uma oferta chega."""
    _row_obra     = _info_row("Obra", nome_obra)
    _row_valor    = _info_row("Valor ofertado", valor_brl)
    _row_compra   = _info_row("Comprador", nome_comprador)
    _row_prazo    = _info_row("Prazo para a editora responder", deadline_str)
    _tabela       = _info_table(_row_obra, _row_valor, _row_compra, _row_prazo)
    body = (
        '<h2 style="margin:0 0 6px;font-size:22px;font-weight:800;color:#09090B;">'
        "Oferta de licenciamento em andamento"
        "</h2>"
        '<p style="margin:0 0 20px;font-size:14px;color:#52525B;line-height:1.6;">'
        f"Olá, <strong>{nome or 'compositor'}</strong>. Uma oferta de licenciamento "
        "foi recebida para a sua obra e está aguardando a aprovação da editora vinculada."
        "</p>"
        f"\n{_tabela}\n"
        '<p style="margin:20px 0 0;font-size:13px;color:#52525B;line-height:1.6;">'
        "Você será notificado assim que a editora assinar o contrato e a transação "
        "for concluída. Não é necessário nenhuma ação da sua parte agora."
        "</p>"
    )
    text = (
        f"Gravan — Oferta de licenciamento em andamento\n\n"
        f"Obra: {nome_obra}\nValor: {valor_brl}\nComprador: {nome_comprador}\n"
        f"Prazo da editora: {deadline_str}\n\n"
        "Você será avisado quando a transação for concluída."
    )
    return _wrap_html(f"Oferta recebida — {nome_obra} — Gravan", body, accent="#1d4ed8"), text


def render_oferta_lembrete_compositor_email(
    nome: str, nome_obra: str, valor_brl: str, horas_restantes: int,
) -> tuple[str, str]:
    """Lembrete ao compositor de que o prazo está se esgotando."""
    _row_obra   = _info_row("Obra", nome_obra)
    _row_valor  = _info_row("Valor ofertado", valor_brl)
    _row_horas  = _info_row("Horas úteis restantes", f"~{horas_restantes}h")
    _tabela     = _info_table(_row_obra, _row_valor, _row_horas)
    _alerta     = _alert(
        "Se o prazo expirar sem resposta da editora, a oferta será cancelada "
        "e o valor estornado ao comprador. Entre em contato com sua editora se necessário.",
        "#FEF3C7", "#D97706", "#78350F",
    )
    body = (
        '<h2 style="margin:0 0 6px;font-size:22px;font-weight:800;color:#09090B;">'
        "Prazo da oferta se esgotando"
        "</h2>"
        '<p style="margin:0 0 20px;font-size:14px;color:#52525B;line-height:1.6;">'
        f"Olá, <strong>{nome or 'compositor'}</strong>. A oferta de licenciamento para a "
        f'obra <strong>"{nome_obra}"</strong> ainda não foi respondida pela editora.'
        "</p>"
        f"\n{_tabela}\n"
        f"\n{_alerta}\n"
    )
    text = (
        f"Gravan — Prazo da oferta se esgotando\n\n"
        f"Obra: {nome_obra}\nFaltam ~{horas_restantes}h úteis.\n"
        "Se a editora não responder, a oferta será cancelada."
    )
    return _wrap_html(f"Lembrete: oferta de \"{nome_obra}\" — Gravan", body, accent="#d97706"), text


def render_oferta_expirada_compositor_email(
    nome: str, nome_obra: str, valor_brl: str,
) -> tuple[str, str]:
    """Notifica o compositor quando a oferta expira sem resposta da editora."""
    _row_obra   = _info_row("Obra", nome_obra)
    _row_valor  = _info_row("Valor da oferta", valor_brl)
    _row_status = _info_row("Status", "Expirada — valor estornado ao comprador")
    _tabela     = _info_table(_row_obra, _row_valor, _row_status)
    body = (
        '<h2 style="margin:0 0 6px;font-size:22px;font-weight:800;color:#09090B;">'
        "Oferta de licenciamento expirada"
        "</h2>"
        '<p style="margin:0 0 20px;font-size:14px;color:#52525B;line-height:1.6;">'
        f"Olá, <strong>{nome or 'compositor'}</strong>. A oferta de licenciamento "
        f'para a obra <strong>"{nome_obra}"</strong> expirou sem resposta da editora '
        "dentro do prazo de 72 horas úteis."
        "</p>"
        f"\n{_tabela}\n"
        '<p style="margin:16px 0 0;font-size:13px;color:#52525B;line-height:1.6;">'
        "O comprador poderá fazer uma nova oferta a qualquer momento. "
        "Se você deseja agilizar futuros licenciamentos, verifique se as informações "
        "da sua editora estão atualizadas na plataforma."
        "</p>"
    )
    text = (
        f"Gravan — Oferta de licenciamento expirada\n\n"
        f"Obra: {nome_obra}\nValor: {valor_brl}\n"
        "A editora não respondeu no prazo. O valor foi estornado ao comprador."
    )
    return _wrap_html(f"Oferta expirada — {nome_obra} — Gravan", body, accent="#d97706"), text


def render_oferta_concluida_compositor_email(
    nome: str, nome_obra: str, valor_brl: str,
) -> tuple[str, str]:
    """Notifica o compositor/coautor quando a oferta é concluída com sucesso."""
    _row_obra   = _info_row("Obra licenciada", nome_obra)
    _row_valor  = _info_row("Valor bruto da transação", valor_brl)
    _row_status = _info_row("Status", "Valor creditado na carteira")
    _tabela     = _info_table(_row_obra, _row_valor, _row_status)
    _alerta     = _alert(
        "Você já pode solicitar o saque do valor na sua área financeira da Gravan.",
        "#F0FDF4", "#16a34a", "#14532D",
    )
    _botao      = _btn("Ver minha carteira", "https://www.gravan.com.br/dashboard", "#16a34a")
    body = (
        '<table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="margin:0 0 20px;">'
        "<tr><td align=\"center\">"
        '<div style="width:56px;height:56px;background-color:#DCFCE7;border-radius:50%;'
        'line-height:56px;text-align:center;font-size:26px;margin:0 auto 12px;">\U0001f4b0</div>'
        '<h2 style="margin:0 0 6px;font-size:22px;font-weight:800;color:#09090B;">'
        "Licenciamento concluído — você recebeu!"
        "</h2>"
        '<p style="margin:0;font-size:14px;color:#52525B;">'
        f"Olá, <strong>{nome or 'compositor'}</strong>. O contrato foi assinado por "
        "todas as partes e sua parte do valor já foi creditada na sua carteira."
        "</p>"
        "</td></tr></table>"
        f"\n{_tabela}\n"
        f"\n{_alerta}\n"
        f"\n{_botao}\n"
    )
    text = (
        f"Gravan — Licenciamento concluído\n\n"
        f"Obra: {nome_obra}\nValor da transação: {valor_brl}\n"
        "Sua parte foi creditada na carteira. Acesse: https://www.gravan.com.br/dashboard"
    )
    return _wrap_html(f"Você recebeu — {nome_obra} — Gravan", body, accent="#16a34a"), text


def render_oferta_concluida_editora_terceira_email(
    nome_editora: str, nome_obra: str, valor_brl: str, comissao_brl: str,
) -> tuple[str, str]:
    """Notifica a editora terceira sobre a conclusão e a comissão creditada."""
    _row_obra      = _info_row("Obra", nome_obra)
    _row_valor     = _info_row("Valor total da transação", valor_brl)
    _row_comissao  = _info_row("Sua comissão (10%)", comissao_brl)
    _row_status    = _info_row("Status", "Creditado na carteira")
    _tabela        = _info_table(_row_obra, _row_valor, _row_comissao, _row_status)
    _alerta        = _alert(
        "Você já pode solicitar o saque da comissão no painel da editora.",
        "#F0FDF4", "#16a34a", "#14532D",
    )
    _botao = _btn("Acessar painel da editora", "https://www.gravan.com.br/editora/dashboard", "#16a34a")
    body = (
        '<table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="margin:0 0 20px;">'
        "<tr><td align=\"center\">"
        '<div style="width:56px;height:56px;background-color:#DCFCE7;border-radius:50%;'
        'line-height:56px;text-align:center;font-size:26px;margin:0 auto 12px;">\U0001f3e6</div>'
        '<h2 style="margin:0 0 6px;font-size:22px;font-weight:800;color:#09090B;">'
        "Comissão creditada"
        "</h2>"
        '<p style="margin:0;font-size:14px;color:#52525B;">'
        f"Olá, <strong>{nome_editora}</strong>. O contrato trilateral foi concluído "
        "e sua comissão editorial foi creditada na carteira Gravan da editora."
        "</p>"
        "</td></tr></table>"
        f"\n{_tabela}\n"
        f"\n{_alerta}\n"
        f"\n{_botao}\n"
    )
    text = (
        f"Gravan — Comissão creditada\n\n"
        f"Obra: {nome_obra}\nValor da transação: {valor_brl}\nSua comissão (10%): {comissao_brl}\n"
        "Acesse: https://www.gravan.com.br/editora/dashboard"
    )
    return _wrap_html(f"Comissão creditada — {nome_obra} — Gravan", body, accent="#16a34a"), text
