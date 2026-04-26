"""
Gerador do TERMO DE AGREGAÇÃO E REPRESENTAÇÃO EDITORIAL.

Esse termo é gravado de forma imutável dentro do registro do convite (coluna
`termo_html` em `agregado_convites`). Tanto a editora quanto o artista assinam
digitalmente — a assinatura da editora se dá no momento do envio do convite e
a do artista no momento do aceite. Os dois lados ficam vinculados a esse
documento, que pode ser exibido a qualquer tempo (como prova legal).

Fundamentação:
  • Lei 9.610/98 (Direitos Autorais) — Capítulo III "Cessão e Edição"
  • Lei 13.709/18 (LGPD) — registro de consentimento explícito
"""
from datetime import datetime, timezone

VERSAO_ATUAL = "v1"


def _hoje_extenso() -> str:
    meses = ["janeiro", "fevereiro", "março", "abril", "maio", "junho",
             "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]
    d = datetime.now(timezone.utc)
    return f"{d.day} de {meses[d.month - 1]} de {d.year}"


def _mask_cpf(cpf: str) -> str:
    """Mostra só os dois últimos dígitos. Ex.: 123.456.789-12 → ***.***.***-12"""
    if not cpf:
        return ""
    digits = "".join(c for c in cpf if c.isdigit())
    if len(digits) < 4:
        return "***"
    return f"***.***.***-{digits[-2:]}"


def gerar_termo_html(
    *,
    editora: dict,
    artista: dict | None,
    email_artista: str,
    modo: str,
) -> str:
    """
    Monta o termo HTML completo. `editora` deve conter:
       razao_social, cnpj (decriptado se possível, senão mascarado),
       responsavel_nome, responsavel_cpf (decriptado, será mascarado aqui),
       endereco_*.
    `artista` pode ser None (modo='cadastrar' sem perfil prévio).

    Retorna HTML pronto para ser exibido / enviado por e-mail / armazenado.
    """
    razao    = (editora.get("razao_social") or editora.get("nome_completo") or "Editora").strip()
    fantasia = (editora.get("nome_fantasia") or "").strip()
    cnpj     = (editora.get("cnpj_display") or editora.get("cnpj") or "").strip()
    resp     = (editora.get("responsavel_nome") or "").strip()
    resp_cpf_mask = _mask_cpf(editora.get("responsavel_cpf_display") or editora.get("responsavel_cpf") or "")
    end_completo = ", ".join(filter(None, [
        editora.get("endereco_rua"),
        editora.get("endereco_numero"),
        editora.get("endereco_bairro"),
        editora.get("endereco_cidade"),
        editora.get("endereco_uf"),
        editora.get("endereco_cep"),
    ]))

    nome_artista = ((artista or {}).get("nome_completo") or "").strip() or "(a ser confirmado pelo artista)"
    artistico    = ((artista or {}).get("nome_artistico") or "").strip()

    modo_legenda = (
        "cadastro inicial pela editora (Cláusula 4.1)"
        if modo == "cadastrar"
        else "convite a artista já cadastrado na plataforma (Cláusula 4.2)"
    )

    cabecalho_fantasia = f' (nome fantasia: <strong>{fantasia}</strong>)' if fantasia else ''

    return f"""
<div style="font-family:'Helvetica Neue',Arial,sans-serif;color:#111;line-height:1.55;font-size:13px">
  <h2 style="text-align:center;font-size:16px;margin:0 0 4px">
    TERMO DE AGREGAÇÃO E REPRESENTAÇÃO EDITORIAL
  </h2>
  <p style="text-align:center;color:#666;font-size:11px;margin:0 0 18px">
    Versão {VERSAO_ATUAL} — emitido eletronicamente em {_hoje_extenso()} via plataforma Gravan
  </p>

  <h3 style="font-size:13px;margin:18px 0 6px">DAS PARTES</h3>
  <p>
    <strong>EDITORA / OUTORGADA:</strong> {razao}{cabecalho_fantasia},
    inscrita no CNPJ <strong>{cnpj or 'a confirmar'}</strong>, com sede em {end_completo or 'endereço cadastrado'},
    neste ato representada por <strong>{resp or 'seu responsável legal'}</strong> (CPF {resp_cpf_mask or 'cadastrado'}),
    devidamente autorizado(a) e plenamente identificado(a) na plataforma Gravan.
  </p>
  <p>
    <strong>ARTISTA / OUTORGANTE:</strong> {nome_artista}{(' ("' + artistico + '")') if artistico else ''},
    titular do e-mail <strong>{email_artista}</strong>, identificado eletronicamente na plataforma
    Gravan no ato do aceite digital deste termo.
  </p>

  <h3 style="font-size:13px;margin:18px 0 6px">CLÁUSULA 1ª — DO OBJETO</h3>
  <p>
    O ARTISTA, na qualidade de autor e titular originário dos direitos autorais sobre suas
    composições musicais (letra e melodia), nomeia e constitui a EDITORA como sua
    <strong>representante editorial</strong> perante a plataforma Gravan, conferindo-lhe
    poderes para administrar, em nome do ARTISTA, as obras que vierem a ser cadastradas
    e expressamente vinculadas ao seu catálogo na plataforma.
  </p>

  <h3 style="font-size:13px;margin:18px 0 6px">CLÁUSULA 2ª — DOS PODERES OUTORGADOS</h3>
  <p>São conferidos à EDITORA, exclusivamente no âmbito da plataforma Gravan, os seguintes poderes:</p>
  <ol style="padding-left:18px;margin:6px 0">
    <li>Cadastrar, editar e publicar obras em nome do ARTISTA;</li>
    <li>Receber, avaliar e <strong>responder a ofertas de licenciamento</strong> recebidas via plataforma;</li>
    <li>Negociar valores, prazos e condições comerciais dos licenciamentos;</li>
    <li>Assinar eletronicamente, em nome do ARTISTA, contratos de licenciamento gerados pela plataforma;</li>
    <li>Receber valores oriundos das licenças e repassá-los na forma da Cláusula 5ª;</li>
    <li>Praticar todos os atos administrativos correlatos, conforme funcionalidades disponíveis no painel da editora.</li>
  </ol>

  <h3 style="font-size:13px;margin:18px 0 6px">CLÁUSULA 3ª — DAS DECLARAÇÕES E GARANTIAS DA EDITORA</h3>
  <p>A EDITORA <strong>declara, sob as penas da lei</strong>, que:</p>
  <ol style="padding-left:18px;margin:6px 0">
    <li>Possui plena capacidade jurídica e está regularmente constituída;</li>
    <li>Detém os <strong>direitos de administração editorial</strong> das obras do ARTISTA aqui agregado, ou os obterá mediante o aceite digital deste termo, por instrumento particular válido entre as partes;</li>
    <li>Indenizará e manterá <strong>indene a plataforma Gravan</strong>, seus sócios, representantes e colaboradores, de qualquer reclamação, ação ou demanda — judicial ou extrajudicial — proposta por terceiros (inclusive pelo próprio ARTISTA) decorrente de eventual ausência, vício ou excesso dos poderes ora declarados;</li>
    <li>Não utilizará os dados pessoais do ARTISTA para finalidade diversa da execução deste termo, em conformidade com a LGPD (Lei 13.709/18).</li>
  </ol>

  <h3 style="font-size:13px;margin:18px 0 6px">CLÁUSULA 4ª — DO ACEITE DIGITAL</h3>
  <p>4.1. <strong>Cadastro inicial pela editora.</strong> Quando o ARTISTA ainda não possui perfil ativo, a EDITORA poderá cadastrá-lo informando seus dados pessoais. O ARTISTA receberá convite para definir senha e acessar a plataforma; ao primeiro acesso, deverá <strong>aceitar ou recusar</strong> este termo. Em caso de recusa, o vínculo será desfeito automaticamente e os dados ficarão em poder do próprio ARTISTA.</p>
  <p>4.2. <strong>Convite a artista existente.</strong> Quando o ARTISTA já possui perfil, receberá notificação na plataforma e por e-mail. A vinculação somente se efetiva mediante aceite eletrônico expresso, registrado com data, hora e endereço IP.</p>
  <p>4.3. Modo deste convite: <em>{modo_legenda}</em>.</p>

  <h3 style="font-size:13px;margin:18px 0 6px">CLÁUSULA 5ª — DOS REPASSES E TRANSPARÊNCIA</h3>
  <p>
    A divisão financeira de cada licenciamento obedecerá ao percentual pactuado em contrato
    específico de edição (registrado pela plataforma quando aplicável). Na ausência de pactuação
    específica, presume-se a divisão padrão da plataforma vigente à época do licenciamento. O
    ARTISTA terá <strong>visibilidade integral</strong>, em seu painel, de todas as obras administradas, ofertas
    recebidas, contratos assinados e valores recebidos pela EDITORA em seu nome.
  </p>

  <h3 style="font-size:13px;margin:18px 0 6px">CLÁUSULA 6ª — DA REVOGAÇÃO</h3>
  <p>
    O presente vínculo poderá ser desfeito a qualquer tempo pelo ARTISTA, por ato unilateral
    realizado em seu painel ("Desvincular editora"), sem prejuízo dos contratos de licenciamento
    já assinados, que permanecerão válidos até seu termo final, conservando-se o pagamento dos
    repasses devidos.
  </p>

  <h3 style="font-size:13px;margin:18px 0 6px">CLÁUSULA 7ª — DA RESPONSABILIDADE DA PLATAFORMA</h3>
  <p>
    A Gravan atua como <strong>plataforma intermediária</strong>, oferecendo a infraestrutura tecnológica
    para o registro, administração e licenciamento das obras. Em nenhuma hipótese a Gravan
    será responsabilizada por divergências entre EDITORA e ARTISTA quanto à titularidade
    ou divisão dos direitos autorais — observado o disposto na Cláusula 3.3.
  </p>

  <h3 style="font-size:13px;margin:18px 0 6px">CLÁUSULA 8ª — DA LEI E DO FORO</h3>
  <p>
    Este termo rege-se pelas leis da República Federativa do Brasil, em especial pela
    Lei 9.610/98 e pela Lei 13.709/18. Fica eleito o foro da comarca de domicílio do
    ARTISTA para dirimir eventuais controvérsias.
  </p>

  <p style="margin-top:22px;padding:12px;background:#FAFAFA;border-left:3px solid #BE123C;font-size:12px;color:#444">
    <strong>Aceite digital da EDITORA:</strong> {resp or 'Responsável legal'} — registrado eletronicamente em {_hoje_extenso()}.<br>
    <strong>Aceite digital do ARTISTA:</strong> a ser registrado no momento da aprovação na plataforma.
  </p>
</div>
""".strip()


def gerar_termo_text(editora: dict, artista: dict | None, email_artista: str, modo: str) -> str:
    """Versão texto enxuta para fallback de e-mail."""
    razao = (editora.get("razao_social") or "Editora").strip()
    return (
        f"TERMO DE AGREGAÇÃO E REPRESENTAÇÃO EDITORIAL — Gravan\n\n"
        f"Editora: {razao}\nArtista: {email_artista}\nModo: {modo}\n\n"
        f"Por este termo, o ARTISTA outorga à EDITORA poderes para administrar suas obras\n"
        f"musicais cadastradas na plataforma Gravan, nos limites da Lei 9.610/98 e da LGPD.\n"
        f"O termo completo está disponível na plataforma para leitura e aceite expresso.\n"
    )
