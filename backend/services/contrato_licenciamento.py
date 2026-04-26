"""
Serviço: geração do Contrato de Autorização para Gravação e Exploração
de Obra Musical. Disparado quando uma transação Stripe é confirmada.
"""
import hashlib
from datetime import datetime, timezone
from decimal import Decimal

from db.supabase_client import get_supabase


TEMPLATE_LICENCIAMENTO = """CONTRATO DE AUTORIZAÇÃO PARA GRAVAÇÃO E EXPLORAÇÃO DE OBRA MUSICAL

Pelo presente instrumento particular, de um lado:

AUTOR(ES):
{{autores_bloco}}

doravante denominado(s) "AUTOR(ES)".

E, de outro lado:

INTÉRPRETE/PRODUTOR:
Nome/Razão Social: {{interprete_nome}}
CPF/CNPJ: {{interprete_cpf}}
Endereço: {{interprete_endereco}}
Cidade/UF: {{interprete_cidade_uf}}

doravante denominado "LICENCIADO".

Têm entre si justo e contratado o seguinte:

CLÁUSULA 1 — OBJETO

O presente contrato tem por objeto a autorização para fixação da obra musical em fonograma, bem como sua exploração comercial pelo LICENCIADO.

Título da Obra: {{obra_nome}}

CORPO DA OBRA, conforme cadastrada pelo(s) AUTOR(ES) na plataforma GRAVAN, parte integrante e indissociável deste Contrato:

— CORPO DA OBRA —
{{obra_letra}}
— FIM DO CORPO DA OBRA —

CLÁUSULA 2 — CESSÃO DE DIREITOS

O(s) AUTOR(ES) autoriza(m), de forma irrevogável e irretratável, o LICENCIADO a:
I. Reproduzir a obra em qualquer formato ou suporte;
II. Distribuir e comercializar a obra em meios físicos e digitais;
III. Disponibilizar a obra em plataformas de streaming, incluindo, mas não se limitando a Spotify e Apple Music;
IV. Utilizar a obra em redes sociais e plataformas digitais;
V. Sincronizar a obra com conteúdos audiovisuais.

CLÁUSULA 3 — TERRITÓRIO, PRAZO, RESCISÃO E EXCLUSIVIDADE

A presente autorização é concedida em caráter mundial, pelo prazo de 5 (cinco) anos, contados da data de emissão deste instrumento.

Parágrafo Primeiro — Rescisão: O presente contrato poderá ser rescindido por qualquer das partes mediante comunicação formal e expressa, enviada por e-mail aos endereços indicados neste instrumento, com antecedência mínima de 30 (trinta) dias da efetiva rescisão. Toda e qualquer exploração comercial realizada durante a vigência, inclusive nos 30 (trinta) dias seguintes à comunicação, reputa-se válida e definitiva.

Parágrafo Segundo — Não exclusividade (regra geral): Salvo se este licenciamento tiver sido contratado em caráter EXCLUSIVO (oferta de exclusividade aceita e paga por meio da plataforma GRAVAN), a autorização é concedida em caráter NÃO EXCLUSIVO, podendo o(s) AUTOR(ES) licenciar a mesma obra a terceiros.

Parágrafo Terceiro — Licença de exclusividade: Quando o licenciamento for contratado em caráter EXCLUSIVO, o(s) AUTOR(ES) e a plataforma GRAVAN obrigam-se a NÃO licenciar a mesma obra a terceiros pelo prazo de 5 (cinco) anos contados da data de emissão deste instrumento. Nessa hipótese, eventuais contratos pré-existentes de licenciamento da mesma obra serão automaticamente notificados de rescisão pela GRAVAN, na forma do Parágrafo Primeiro, indicando como motivo a venda de exclusividade.

Parágrafo Quarto — Renovação: Findo o prazo, o contrato poderá ser renovado mediante acordo escrito entre as partes. A não renovação não impede o LICENCIADO de continuar explorando as gravações realizadas durante o período contratual.

CLÁUSULA 4 — GARANTIA DE TITULARIDADE

O(s) AUTOR(ES) declara(m) que:
I. São legítimos titulares da obra;
II. A obra é original e não infringe direitos de terceiros;
III. Assumem total responsabilidade por eventuais reivindicações.

O LICENCIADO fica isento de qualquer responsabilidade perante terceiros.

CLÁUSULA 5 — REMUNERAÇÃO

5.1 — BUYOUT (VENDA DA COMPOSIÇÃO)

O LICENCIADO pagará o valor bruto de {{valor_buyout_extenso}} referente à aquisição da composição por meio da plataforma GRAVAN.

5.2 — TAXA DE INTERMEDIAÇÃO DA PLATAFORMA GRAVAN

Sobre o valor bruto pago pelo LICENCIADO incidirá uma taxa de intermediação devida à plataforma GRAVAN, no percentual de {{plataforma_pct}}% ({{plataforma_pct_extenso}}), correspondente ao plano de assinatura vigente do AUTOR PRINCIPAL na data deste licenciamento ({{plano_titular_label}}). O saldo remanescente, equivalente a {{liquido_autores_pct}}% do valor bruto, será distribuído entre o(s) AUTOR(ES) na proporção declarada na CLÁUSULA 10 (SPLIT).

Parágrafo Único: Os percentuais aplicados pela plataforma são: 20% (vinte por cento) para titular no plano GRÁTIS e 15% (quinze por cento) para titular no plano PRO ativo na data da venda.

5.3 — ROYALTIES AUTORAIS (EXECUÇÃO PÚBLICA)

Os rendimentos provenientes de execução pública arrecadados pelo ECAD serão distribuídos da seguinte forma:
- 85% (oitenta e cinco por cento) para o(s) AUTOR(ES) e coautores;
- 10% (dez por cento) para o INTÉRPRETE;
- 5% (cinco por cento) para a EDITORA GRAVAN.

CLÁUSULA 6 — CRÉDITOS E IDENTIFICAÇÃO

O LICENCIADO compromete-se a creditar corretamente o(s) AUTOR(ES) utilizando o(s) seguinte(s) nome(s) autoral(is)/artístico(s): {{autores_nomes_artisticos}}.

Dados técnicos:
- ISRC: {{isrc}}
- ISWC: {{iswc}}

CLÁUSULA 7 — EXPLORAÇÃO

O LICENCIADO terá liberdade para:
- Definir estratégias de lançamento;
- Distribuir a obra globalmente;
- Firmar parcerias e sublicenças.

CLÁUSULA 8 — IRRETRATABILIDADE DA EXPLORAÇÃO

Ressalvado o direito de rescisão previsto na CLÁUSULA 3, Parágrafo Primeiro, este contrato é celebrado em caráter irretratável quanto às explorações comerciais e gravações já realizadas durante a sua vigência.

CLÁUSULA 9 — DISPOSIÇÕES GERAIS

I. Este contrato obriga as partes e seus sucessores;
II. Pode ser firmado digitalmente, nos termos da MP nº 2.200-2/2001 e Lei nº 14.063/2020;
III. Integra as regras da plataforma GRAVAN.

CLÁUSULA 10 — DIVISÃO DE DIREITOS ENTRE COAUTORES (SPLIT)

Fica estabelecido que a divisão dos direitos autorais entre os coautores é a seguinte:
{{split_lista}}

Parágrafo Primeiro: A divisão acima foi declarada pelos próprios autores na plataforma GRAVAN no momento do cadastro da obra.

Parágrafo Segundo: Salvo acordo formal em contrário, devidamente registrado por escrito e assinado por todos os coautores, prevalecerá a divisão acima.

Parágrafo Terceiro: Os valores decorrentes de remuneração, royalties e quaisquer receitas relacionadas à obra serão distribuídos conforme esta proporção.

Parágrafo Quarto: Cada coautor declara estar ciente e de acordo com o presente critério de divisão.

CLÁUSULA 11 — FORO

Fica eleito o foro da comarca da cidade do Rio de Janeiro/RJ, com renúncia de qualquer outro, por mais privilegiado que seja.

ASSINATURAS ELETRÔNICAS

Este instrumento é firmado eletronicamente, com registro de data, hora, IP anonimizado (SHA-256) e hash de integridade do conteúdo. A aceitação eletrônica por cada parte configura assinatura válida e vinculante (MP 2.200-2/2001; Lei 14.063/2020).

Data de emissão: {{data_emissao}}
Hash SHA-256 do documento: {{conteudo_hash}}
"""


def _moeda(cents: int) -> str:
    valor = Decimal(cents) / Decimal(100)
    s = f"R$ {valor:,.2f}"
    # Formato BR: 1,234.56 → 1.234,56
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def _endereco(p: dict) -> str:
    return ", ".join(filter(None, [
        p.get("endereco_rua"),
        p.get("endereco_numero"),
        p.get("endereco_compl"),
        p.get("endereco_bairro"),
    ])) or "Não informado"


def _cidade_uf(p: dict) -> str:
    c = p.get("endereco_cidade")
    uf = p.get("endereco_uf")
    if c and uf: return f"{c}/{uf}"
    return c or uf or "Não informado"


def _info_plano(titular: dict) -> dict:
    """Retorna labels e percentuais aplicáveis ao plano do titular para uso em
    cláusulas dos contratos (taxa Gravan e líquido autores)."""
    from services.finance import fee_rate_for_plano, EDITORA_RATE
    plano = (titular or {}).get("plano", "STARTER")
    status_ass = (titular or {}).get("status_assinatura", "inativa")
    is_pro = (plano == "PRO" and status_ass in ("ativa", "cancelada", "past_due"))
    rate = fee_rate_for_plano("PRO" if is_pro else "STARTER")
    plataforma_pct = int(round(float(rate) * 100))
    plano_label = "Plano PRO" if is_pro else "Plano GRÁTIS"
    extenso = {15: "quinze por cento", 20: "vinte por cento"}.get(plataforma_pct, f"{plataforma_pct} por cento")
    editora_pct = int(round(float(EDITORA_RATE) * 100))
    editora_extenso = {10: "dez por cento"}.get(editora_pct, f"{editora_pct} por cento")
    return {
        "plataforma_pct": plataforma_pct,
        "plataforma_pct_extenso": extenso,
        "plano_titular_label": plano_label,
        "editora_pct": editora_pct,
        "editora_pct_extenso": editora_extenso,
        "liquido_autores_pct": 100 - plataforma_pct,
        "liquido_autores_pct_trilateral": 100 - plataforma_pct - editora_pct,
    }


def _decrypt(val: str) -> str:
    """Decripta CPF/RG se estiver criptografado."""
    if not val:
        return ""
    try:
        from utils.crypto import decrypt_pii
        return decrypt_pii(val) or val
    except Exception:
        return val


def gerar_contrato_licenciamento(transacao_id: str, ip_remote: str | None = None) -> dict | None:
    """
    Dispara a criação do contrato de licenciamento para uma transação confirmada.
    Idempotente: se já existe um contrato para essa transação, retorna o existente.

    Regra: se o titular da obra é AGREGADO de uma editora no momento da geração
    (perfis.publisher_id preenchido), o contrato gerado é TRILATERAL — incluindo
    a editora como parte signatária. Caso contrário, contrato bilateral padrão.
    """
    sb = get_supabase()

    # 1. Transação
    tx = sb.table("transacoes").select("*").eq("id", transacao_id).single().execute()
    if not tx.data:
        return None
    tx = tx.data
    if tx.get("status") != "confirmada":
        return None

    # 2. Já existe contrato?
    exist = sb.table("contracts").select("id").eq("transacao_id", transacao_id).limit(1).execute()
    if exist.data:
        return sb.table("contracts").select("*").eq("id", exist.data[0]["id"]).single().execute().data

    # 3. Obra + titular + coautorias
    obra = sb.table("obras").select("*").eq("id", tx["obra_id"]).single().execute().data
    if not obra:
        return None

    titular = sb.table("perfis").select("*").eq("id", obra["titular_id"]).single().execute().data or {}
    buyer   = sb.table("perfis").select("*").eq("id", tx["comprador_id"]).single().execute().data or {}

    # 3.1 — Dispatcher: se titular é agregado de uma editora, gera trilateral
    if titular.get("publisher_id"):
        try:
            return gerar_contrato_trilateral_agregado(
                transacao_id=transacao_id,
                tx=tx,
                obra=obra,
                titular=titular,
                buyer=buyer,
                ip_remote=ip_remote,
            )
        except Exception as e:
            # Se o trilateral por agregação falhar, registra e cai para o bilateral.
            try:
                sb.table("contract_events").insert({
                    "contract_id": None,
                    "event_type":  "trilateral_agregado_fallback",
                    "payload":     {"erro": str(e), "transacao_id": transacao_id},
                }).execute()
            except Exception:
                pass

    coaut = sb.table("coautorias").select("perfil_id, share_pct").eq("obra_id", obra["id"]).execute().data or []
    if not coaut:
        coaut = [{"perfil_id": titular["id"], "share_pct": 100}]

    # Nomes dos coautores
    ids = list({c["perfil_id"] for c in coaut})
    perfis = sb.table("perfis").select("id, nome, nome_artistico, nome_completo, cpf, rg, endereco_rua, endereco_numero, endereco_compl, endereco_bairro, endereco_cidade, endereco_uf, email").in_("id", ids).execute().data or []
    por_id = {p["id"]: p for p in perfis}

    # 4. Monta blocos do template
    autores_bloco_partes = []
    autores_nomes_artisticos = []
    split_lista_partes = []

    # Autor principal (titular) primeiro
    ordered = sorted(coaut, key=lambda c: 0 if c["perfil_id"] == titular["id"] else 1)
    for c in ordered:
        p = por_id.get(c["perfil_id"], {})
        is_titular = c["perfil_id"] == titular["id"]
        papel = "AUTOR PRINCIPAL" if is_titular else "COAUTOR"
        bloco = (
            f"[{papel}]\n"
            f"Nome: {p.get('nome_completo') or p.get('nome') or '—'}\n"
            f"CPF: {_decrypt(p.get('cpf', '')) or 'Não informado'}\n"
            f"RG: {_decrypt(p.get('rg', '')) or 'Não informado'}\n"
            f"Endereço: {_endereco(p)}\n"
            f"Cidade/UF: {_cidade_uf(p)}\n"
        )
        autores_bloco_partes.append(bloco)
        autores_nomes_artisticos.append(p.get("nome_artistico") or p.get("nome") or "—")
        split_lista_partes.append(
            f"- {p.get('nome_completo') or p.get('nome') or '—'}: {float(c['share_pct']):.2f}%"
        )

    info = _info_plano(titular)
    conteudo = (TEMPLATE_LICENCIAMENTO
        .replace("{{autores_bloco}}",          "\n".join(autores_bloco_partes).strip())
        .replace("{{interprete_nome}}",        buyer.get("nome_completo") or buyer.get("nome") or "—")
        .replace("{{interprete_cpf}}",         _decrypt(buyer.get("cpf","")) or "Não informado")
        .replace("{{interprete_endereco}}",    _endereco(buyer))
        .replace("{{interprete_cidade_uf}}",   _cidade_uf(buyer))
        .replace("{{obra_nome}}",              obra.get("nome","—"))
        .replace("{{obra_letra}}",             (obra.get("letra") or "").strip() or "—")
        .replace("{{valor_buyout_extenso}}",   _moeda(tx["valor_cents"]))
        .replace("{{autores_nomes_artisticos}}", ", ".join(autores_nomes_artisticos))
        .replace("{{isrc}}",                   obra.get("isrc") or "a definir após lançamento")
        .replace("{{iswc}}",                   obra.get("iswc") or "a definir após lançamento")
        .replace("{{split_lista}}",            "\n".join(split_lista_partes))
        .replace("{{plataforma_pct}}",         str(info["plataforma_pct"]))
        .replace("{{plataforma_pct_extenso}}", info["plataforma_pct_extenso"])
        .replace("{{plano_titular_label}}",    info["plano_titular_label"])
        .replace("{{liquido_autores_pct}}",    str(info["liquido_autores_pct"]))
        .replace("{{data_emissao}}",           datetime.utcnow().strftime("%d/%m/%Y às %H:%M UTC"))
    )

    # Hash do conteúdo
    content_hash = hashlib.sha256(conteudo.encode("utf-8")).hexdigest()
    conteudo = conteudo.replace("{{conteudo_hash}}", content_hash)

    # HTML formatado (básico) — para visualização
    html_lines = []
    for bloco in conteudo.split("\n\n"):
        b = bloco.strip()
        if not b: continue
        if b.isupper() or b.startswith("CLÁUSULA") or b.startswith("CONTRATO"):
            html_lines.append(f"<h3>{b}</h3>")
        else:
            html_lines.append(f"<p>{b.replace(chr(10), '<br/>')}</p>")
    contract_html = "\n".join(html_lines)

    # 5. Cria contract + signers
    insert = sb.table("contracts").insert({
        "transacao_id":   transacao_id,
        "obra_id":        obra["id"],
        "seller_id":      titular["id"],
        "buyer_id":       buyer["id"],
        "valor_cents":    tx["valor_cents"],
        "contract_html":  contract_html,
        "contract_text":  conteudo,
        "status":         "pendente",
    }).execute()
    contract = insert.data[0]

    # Signers: todos os coautores (role autor/coautor) + intérprete
    signers = []
    for c in ordered:
        signers.append({
            "contract_id": contract["id"],
            "user_id":     c["perfil_id"],
            "role":        "autor" if c["perfil_id"] == titular["id"] else "coautor",
            "share_pct":   float(c["share_pct"]),
        })
    signers.append({
        "contract_id": contract["id"],
        "user_id":     buyer["id"],
        "role":        "interprete",
        "share_pct":   None,
    })
    try:
        sb.table("contract_signers").insert(signers).execute()
    except Exception:
        pass

    # Log do evento
    try:
        sb.table("contract_events").insert({
            "contract_id": contract["id"],
            "event_type":  "created",
            "payload":     {"hash": content_hash, "ip": (ip_remote or "")[:32]},
        }).execute()
    except Exception:
        pass

    return contract


def gerar_contrato_trilateral_agregado(
    transacao_id: str,
    tx: dict,
    obra: dict,
    titular: dict,
    buyer: dict,
    ip_remote: str | None = None,
) -> dict | None:
    """
    Gera o contrato TRILATERAL para uma transação direta (Stripe) quando
    o titular da obra é AGREGADO de uma editora cadastrada na plataforma
    (perfis.publisher_id preenchido).

    Partes: Autor(es) + Editora-mãe (publisher) + Gravan (intermediária) + Comprador.
    Idempotente.
    """
    sb = get_supabase()

    # 1) Editora à qual o titular está vinculado
    editora = sb.table("perfis").select("*").eq("id", titular["publisher_id"]).maybe_single().execute()
    editora = (editora.data if editora else None) or {}
    if not editora.get("id"):
        # Sem editora válida → cai para o bilateral
        raise RuntimeError("publisher_id do titular não encontrado em perfis")

    # 2) Coautores
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

    autores_bloco = []
    split_lista = []
    ordered = sorted(coaut, key=lambda c: 0 if c["perfil_id"] == titular["id"] else 1)
    for c in ordered:
        p = por_id.get(c["perfil_id"], {})
        is_titular = c["perfil_id"] == titular["id"]
        autores_bloco.append(
            f"[{'AUTOR PRINCIPAL' if is_titular else 'COAUTOR'}]\n"
            f"Nome: {p.get('nome_completo') or p.get('nome') or '—'}\n"
            f"CPF: {_decrypt(p.get('cpf','')) or 'Não informado'}\n"
            f"RG: {_decrypt(p.get('rg','')) or 'Não informado'}\n"
            f"Endereço: {_endereco(p)}\n"
            f"Cidade/UF: {_cidade_uf(p)}\n"
        )
        split_lista.append(
            f"- {p.get('nome_completo') or p.get('nome') or '—'}: {float(c['share_pct']):.2f}%"
        )

    # 3) Endereço/CNPJ da editora
    cnpj_dec = _decrypt(editora.get("cnpj", "")) or "Não informado"
    editora_endereco = ", ".join(filter(None, [
        editora.get("endereco_rua"), editora.get("endereco_numero"),
        editora.get("endereco_compl"), editora.get("endereco_bairro"),
        editora.get("endereco_cidade"), editora.get("endereco_uf"),
    ])) or "Não informado"

    # Cláusula adicional para o caso AGREGADO: reforça o vínculo de agregação
    # já refletido na Cláusula 3.1 (split do buyout).
    clausula_split_editora = (
        "\n\nParágrafo Terceiro: O percentual de 10% (dez por cento) destinado à "
        "EDITORA, conforme item 3.1 acima, decorre do contrato de agregação vigente "
        "entre AUTOR(ES) e EDITORA, ficando a GRAVAN autorizada e obrigada a creditá-lo "
        "automaticamente, em cada licenciamento desta obra, diretamente à EDITORA."
    )

    info = _info_plano(titular)
    conteudo = (TEMPLATE_TRILATERAL
        .replace("{{autores_bloco}}",          "\n".join(autores_bloco).strip())
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
        .replace("{{valor_buyout_extenso}}",   _moeda(tx["valor_cents"]))
        .replace("{{split_lista}}",            "\n".join(split_lista))
        .replace("{{plataforma_pct}}",         str(info["plataforma_pct"]))
        .replace("{{plataforma_pct_extenso}}", info["plataforma_pct_extenso"])
        .replace("{{plano_titular_label}}",    info["plano_titular_label"])
        .replace("{{editora_pct}}",            str(info["editora_pct"]))
        .replace("{{editora_pct_extenso}}",    info["editora_pct_extenso"])
        .replace("{{liquido_autores_pct_trilateral}}", str(info["liquido_autores_pct_trilateral"])) 
        .replace("{{clausula_split_editora}}", clausula_split_editora)
        .replace("{{data_emissao}}",           datetime.utcnow().strftime("%d/%m/%Y às %H:%M UTC"))
    )
    content_hash = hashlib.sha256(conteudo.encode("utf-8")).hexdigest()
    conteudo = conteudo.replace("{{conteudo_hash}}", content_hash)

    # 4) HTML formatado para visualização
    html_lines = []
    for bloco in conteudo.split("\n\n"):
        b = bloco.strip()
        if not b: continue
        if b.isupper() or b.startswith("CLÁUSULA") or b.startswith("CONTRATO"):
            html_lines.append(f"<h3>{b}</h3>")
        else:
            html_lines.append(f"<p>{b.replace(chr(10), '<br/>')}</p>")
    contract_html = "\n".join(html_lines)

    # 5) Insere contrato (trilateral=True, sem oferta_id — diferencia do fluxo
    # de ofertas a editora terceira, que mantém oferta_id preenchido).
    insert = sb.table("contracts").insert({
        "transacao_id":  transacao_id,
        "obra_id":       obra["id"],
        "seller_id":     titular["id"],
        "buyer_id":      buyer["id"],
        "valor_cents":   tx["valor_cents"],
        "contract_html": contract_html,
        "contract_text": conteudo,
        "status":        "pendente",
        "trilateral":    True,
    }).execute()
    contract = insert.data[0]

    # 6) Signers: coautores + editora-mãe + comprador
    signers = []
    for c in ordered:
        signers.append({
            "contract_id": contract["id"],
            "user_id":     c["perfil_id"],
            "role":        "autor" if c["perfil_id"] == titular["id"] else "coautor",
            "share_pct":   float(c["share_pct"]),
        })
    signers.append({
        "contract_id": contract["id"],
        "user_id":     editora["id"],
        "role":        "editora_agregadora",
        "share_pct":   None,
    })
    signers.append({
        "contract_id": contract["id"],
        "user_id":     buyer["id"],
        "role":        "interprete",
        "share_pct":   None,
    })
    try:
        sb.table("contract_signers").insert(signers).execute()
    except Exception as e:
        try:
            sb.table("contract_events").insert({
                "contract_id": contract["id"],
                "event_type":  "signers_error",
                "payload":     {"erro": str(e)},
            }).execute()
        except Exception:
            pass

    try:
        sb.table("contract_events").insert({
            "contract_id": contract["id"],
            "event_type":  "created",
            "payload":     {
                "hash": content_hash,
                "trilateral": True,
                "motivo": "agregado",
                "publisher_id": editora["id"],
                "ip": (ip_remote or "")[:32],
            },
        }).execute()
    except Exception:
        pass

    # 7) Notifica a editora-mãe que há um novo contrato a assinar
    try:
        from services.notificacoes import notify
        notify(
            editora["id"],
            tipo="contrato_pendente",
            titulo="Novo contrato para assinatura",
            mensagem=(
                f'Um agregado seu vendeu a obra "{obra.get("nome","—")}". '
                "Como editora vinculada, sua assinatura é necessária."
            ),
            link=f"/contratos/licenciamento/{contract['id']}",
            payload={"contract_id": contract["id"], "obra_id": obra["id"]},
        )
    except Exception:
        pass

    return contract


TEMPLATE_TRILATERAL = """CONTRATO DE AUTORIZAÇÃO PARA GRAVAÇÃO E EXPLORAÇÃO DE OBRA MUSICAL COM INTERMEDIAÇÃO

Pelo presente instrumento particular, são partes:

AUTOR(ES) DA COMPOSIÇÃO:
{{autores_bloco}}

EDITORA DETENTORA DOS DIREITOS DE EDIÇÃO (TERCEIRA EDITORA):
Razão Social: {{editora_razao}}
CNPJ: {{editora_cnpj}}
Responsável: {{editora_responsavel}}
E-mail: {{editora_email}}
Endereço: {{editora_endereco}}

INTERMEDIÁRIA / PLATAFORMA:
GRAVAN EDITORA MUSICAL LTDA., CNPJ 64.342.514/0001-08, sediada na cidade
do Rio de Janeiro/RJ, doravante "GRAVAN".

LICENCIADO (INTÉRPRETE/PRODUTOR):
Nome/Razão Social: {{interprete_nome}}
Nome Artístico: {{interprete_nome_artistico}}
CPF/CNPJ: {{interprete_cpf}}
RG: {{interprete_rg}}
E-mail: {{interprete_email}}
Endereço: {{interprete_endereco}}
Cidade/UF: {{interprete_cidade_uf}}

Têm entre si justo e contratado o seguinte:

CLÁUSULA 1 — RECONHECIMENTO DE EDIÇÃO PRÉVIA

A obra abaixo identificada possui contrato de edição em vigor com a EDITORA
TERCEIRA. As partes reconhecem expressamente a titularidade dos direitos
editoriais da EDITORA TERCEIRA sobre a composição e a anuência desta para
o licenciamento ora celebrado.

Título da Obra: {{obra_nome}}

CLÁUSULA 2 — OBJETO

O presente contrato tem por objeto a autorização para fixação da obra em
fonograma e sua exploração comercial pelo LICENCIADO, com a participação
da EDITORA TERCEIRA na qualidade de detentora dos direitos editoriais e
da GRAVAN como plataforma intermediária.

CORPO DA OBRA, conforme cadastrada pelo(s) AUTOR(ES) na plataforma
GRAVAN, parte integrante e indissociável deste Contrato:

— CORPO DA OBRA —
{{obra_letra}}
— FIM DO CORPO DA OBRA —

CLÁUSULA 3 — VALOR E ESCROW

O LICENCIADO pagará pelo licenciamento o valor bruto de {{valor_buyout_extenso}},
retido em escrow pela GRAVAN até a assinatura eletrônica de todas as partes.
A liberação do valor ocorre após a assinatura final.

3.1 — DISTRIBUIÇÃO DO VALOR DO BUYOUT

Sobre o valor bruto pago pelo LICENCIADO incidirá:
- {{plataforma_pct}}% ({{plataforma_pct_extenso}}) de taxa de intermediação devida à plataforma GRAVAN, conforme o plano de assinatura vigente do AUTOR PRINCIPAL na data deste licenciamento ({{plano_titular_label}});
- {{editora_pct}}% ({{editora_pct_extenso}}) destinados à EDITORA TERCEIRA, na qualidade de detentora dos direitos editoriais sobre a composição;
- {{liquido_autores_pct_trilateral}}% remanescentes, distribuídos entre o(s) AUTOR(ES) na proporção declarada na CLÁUSULA 7 (SPLIT).

Parágrafo Primeiro: A taxa da plataforma GRAVAN segue a tabela: 20% (vinte por cento) para titular no plano GRÁTIS e 15% (quinze por cento) para titular no plano PRO ativo na data da venda.

Parágrafo Segundo: O percentual de 10% (dez por cento) destinado à EDITORA é fixo e independe do plano de assinatura do AUTOR PRINCIPAL.{{clausula_split_editora}}

CLÁUSULA 4 — DECLARAÇÃO DA EDITORA TERCEIRA

A EDITORA TERCEIRA declara: (i) possuir contrato de edição em vigor sobre a
obra; (ii) ter ciência e concordância com o presente licenciamento;
(iii) responsabilizar-se pela distribuição dos valores cabíveis ao(s)
AUTOR(ES) nos termos do contrato de edição existente entre as partes.

CLÁUSULA 5 — TERRITÓRIO, PRAZO, RESCISÃO E EXCLUSIVIDADE

Autorização mundial, pelo prazo de 5 (cinco) anos contados da data de emissão deste instrumento.

Parágrafo Primeiro — Rescisão: O presente contrato poderá ser rescindido por qualquer das partes mediante comunicação formal e expressa, enviada por e-mail aos endereços indicados neste instrumento, com antecedência mínima de 30 (trinta) dias da efetiva rescisão. As explorações comerciais realizadas durante a vigência, inclusive nos 30 (trinta) dias seguintes à comunicação, reputam-se válidas e definitivas.

Parágrafo Segundo — Não exclusividade (regra geral): Salvo se este licenciamento tiver sido contratado em caráter EXCLUSIVO por meio da plataforma GRAVAN, a autorização é concedida em caráter NÃO EXCLUSIVO, podendo o(s) AUTOR(ES), com a anuência da EDITORA, licenciar a mesma obra a terceiros.

Parágrafo Terceiro — Licença de exclusividade: Quando o licenciamento for contratado em caráter EXCLUSIVO, o(s) AUTOR(ES), a EDITORA e a GRAVAN obrigam-se a NÃO licenciar a mesma obra a terceiros pelo prazo de 5 (cinco) anos contados da data de emissão deste instrumento. Nessa hipótese, eventuais contratos pré-existentes de licenciamento da mesma obra serão automaticamente notificados de rescisão pela GRAVAN, na forma do Parágrafo Primeiro, indicando como motivo a venda de exclusividade.

Parágrafo Quarto — Renovação: Findo o prazo, o contrato poderá ser renovado mediante acordo escrito entre as partes. A não renovação não impede o LICENCIADO de continuar explorando as gravações realizadas durante o período contratual.

CLÁUSULA 6 — ROYALTIES AUTORAIS (EXECUÇÃO PÚBLICA)

Os rendimentos provenientes de execução pública arrecadados pelo ECAD serão
distribuídos da seguinte forma:
- 85% (oitenta e cinco por cento) para o(s) AUTOR(ES) e coautores;
- 10% (dez por cento) para o INTÉRPRETE;
- 5% (cinco por cento) para a EDITORA GRAVAN.

CLÁUSULA 7 — DIVISÃO DECLARADA (SPLIT) ENTRE AUTORES
{{split_lista}}

CLÁUSULA 8 — IRREVOGABILIDADE E ASSINATURAS ELETRÔNICAS

Este instrumento é firmado eletronicamente, com registro de data, hora,
IP anonimizado (SHA-256) e hash de integridade. A aceitação eletrônica de
cada parte configura assinatura válida e vinculante (MP 2.200-2/2001;
Lei 14.063/2020).

CLÁUSULA 9 — FORO

Foro da comarca da cidade do Rio de Janeiro/RJ.

Data de emissão: {{data_emissao}}
Hash SHA-256 do documento: {{conteudo_hash}}
"""


def gerar_contrato_trilateral(oferta_id: str) -> dict | None:
    """
    Gera o contrato trilateral (autor + editora terceira + Gravan + comprador)
    para uma oferta cuja editora já foi cadastrada.
    Idempotente: se já existe, retorna o existente.
    """
    sb = get_supabase()

    of = sb.table("ofertas_licenciamento").select("*").eq("id", oferta_id).single().execute().data
    if not of:
        return None
    if of.get("contrato_id"):
        return sb.table("contracts").select("*").eq("id", of["contrato_id"]).single().execute().data

    obra = sb.table("obras").select("*").eq("id", of["obra_id"]).single().execute().data
    if not obra:
        return None

    titular   = sb.table("perfis").select("*").eq("id", obra["titular_id"]).single().execute().data or {}
    buyer     = sb.table("perfis").select("*").eq("id", of["comprador_id"]).single().execute().data or {}
    editora_t = sb.table("perfis").select("*").eq("id", of["editora_terceira_id"]).single().execute().data or {}

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

    autores_bloco = []
    split_lista = []
    ordered = sorted(coaut, key=lambda c: 0 if c["perfil_id"] == titular["id"] else 1)
    for c in ordered:
        p = por_id.get(c["perfil_id"], {})
        is_titular = c["perfil_id"] == titular["id"]
        autores_bloco.append(
            f"[{'AUTOR PRINCIPAL' if is_titular else 'COAUTOR'}]\n"
            f"Nome: {p.get('nome_completo') or p.get('nome') or '—'}\n"
            f"CPF: {_decrypt(p.get('cpf','')) or 'Não informado'}\n"
            f"RG: {_decrypt(p.get('rg','')) or 'Não informado'}\n"
            f"Endereço: {_endereco(p)}\n"
            f"Cidade/UF: {_cidade_uf(p)}\n"
        )
        split_lista.append(
            f"- {p.get('nome_completo') or p.get('nome') or '—'}: {float(c['share_pct']):.2f}%"
        )

    cnpj_dec = _decrypt(editora_t.get("cnpj", "")) or "Não informado"
    editora_endereco = ", ".join(filter(None, [
        editora_t.get("endereco_rua"), editora_t.get("endereco_numero"),
        editora_t.get("endereco_compl"), editora_t.get("endereco_bairro"),
        editora_t.get("endereco_cidade"), editora_t.get("endereco_uf"),
    ])) or "Não informado"

    info = _info_plano(titular)
    conteudo = (TEMPLATE_TRILATERAL
        .replace("{{autores_bloco}}",          "\n".join(autores_bloco).strip())
        .replace("{{editora_razao}}",          editora_t.get("razao_social") or of["editora_terceira_nome"])
        .replace("{{editora_cnpj}}",           cnpj_dec)
        .replace("{{editora_responsavel}}",    editora_t.get("responsavel_nome") or "—")
        .replace("{{editora_email}}",          editora_t.get("email") or of["editora_terceira_email"])
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
        .replace("{{valor_buyout_extenso}}",   _moeda(of["valor_cents"]))
        .replace("{{split_lista}}",            "\n".join(split_lista))
        .replace("{{plataforma_pct}}",         str(info["plataforma_pct"]))
        .replace("{{plataforma_pct_extenso}}", info["plataforma_pct_extenso"])
        .replace("{{plano_titular_label}}",    info["plano_titular_label"])
        .replace("{{editora_pct}}",            str(info["editora_pct"]))
        .replace("{{editora_pct_extenso}}",    info["editora_pct_extenso"])
        .replace("{{liquido_autores_pct_trilateral}}", str(info["liquido_autores_pct_trilateral"]))
        .replace("{{clausula_split_editora}}", "")
        .replace("{{data_emissao}}",           datetime.utcnow().strftime("%d/%m/%Y às %H:%M UTC"))
    )
    content_hash = hashlib.sha256(conteudo.encode("utf-8")).hexdigest()
    conteudo = conteudo.replace("{{conteudo_hash}}", content_hash)

    html_lines = []
    for bloco in conteudo.split("\n\n"):
        b = bloco.strip()
        if not b: continue
        if b.isupper() or b.startswith("CLÁUSULA") or b.startswith("CONTRATO"):
            html_lines.append(f"<h3>{b}</h3>")
        else:
            html_lines.append(f"<p>{b.replace(chr(10), '<br/>')}</p>")
    contract_html = "\n".join(html_lines)

    insert = sb.table("contracts").insert({
        "transacao_id":  None,
        "obra_id":       obra["id"],
        "seller_id":     titular["id"],
        "buyer_id":      buyer["id"],
        "valor_cents":   of["valor_cents"],
        "contract_html": contract_html,
        "contract_text": conteudo,
        "status":        "pendente",
        "trilateral":    True,
        "oferta_id":     of["id"],
    }).execute()
    contract = insert.data[0]

    signers = []
    for c in ordered:
        signers.append({
            "contract_id": contract["id"],
            "user_id":     c["perfil_id"],
            "role":        "autor" if c["perfil_id"] == titular["id"] else "coautor",
            "share_pct":   float(c["share_pct"]),
        })
    signers.append({
        "contract_id": contract["id"],
        "user_id":     editora_t["id"],
        "role":        "editora_terceira",
        "share_pct":   None,
    })
    signers.append({
        "contract_id": contract["id"],
        "user_id":     buyer["id"],
        "role":        "interprete",
        "share_pct":   None,
    })
    try:
        sb.table("contract_signers").insert(signers).execute()
    except Exception as e:
        # log mas não falha
        try:
            sb.table("contract_events").insert({
                "contract_id": contract["id"],
                "event_type":  "signers_error",
                "payload":     {"erro": str(e)},
            }).execute()
        except Exception:
            pass

    try:
        sb.table("contract_events").insert({
            "contract_id": contract["id"],
            "event_type":  "created",
            "payload":     {"hash": content_hash, "trilateral": True, "oferta_id": of["id"]},
        }).execute()
    except Exception:
        pass

    return contract


def aceitar_contrato(contract_id: str, user_id: str, ip_hash: str | None = None) -> dict:
    """Marca o signer como assinado. Se todos assinaram → status=concluído."""
    sb = get_supabase()
    upd = sb.table("contract_signers").update({
        "signed":    True,
        "signed_at": datetime.now(timezone.utc).isoformat(),
        "ip_hash":   ip_hash,
    }).eq("contract_id", contract_id).eq("user_id", user_id).execute()
    if not upd.data:
        raise ValueError("Você não é uma das partes deste contrato.")

    # Log do evento
    try:
        sb.table("contract_events").insert({
            "contract_id": contract_id,
            "user_id":     user_id,
            "event_type":  "signed",
            "payload":     {"ip": (ip_hash or "")[:32]},
        }).execute()
    except Exception:
        pass

    # Notifica o próprio signatário que sua assinatura foi registrada
    try:
        from services.notificacoes import notify
        ctr_info = sb.table("contracts").select("obra_id, buyer_id, seller_id").eq("id", contract_id).single().execute().data or {}
        obra_row = sb.table("obras").select("nome").eq("id", ctr_info.get("obra_id")).single().execute().data or {}
        obra_nome = obra_row.get("nome") or "obra"
        notify(
            user_id,
            tipo="contrato_assinado",
            titulo="Assinatura registrada",
            mensagem=f'Sua assinatura no contrato da obra "{obra_nome}" foi registrada com sucesso.',
            link=f"/contratos/licenciamento/{contract_id}",
            payload={"contract_id": contract_id},
        )
    except Exception:
        pass

    # Todos assinaram?
    signers = sb.table("contract_signers").select("signed").eq("contract_id", contract_id).execute().data or []
    todos = signers and all(s.get("signed") for s in signers)
    if todos:
        sb.table("contracts").update({
            "status":       "concluído",
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", contract_id).execute()
        try:
            sb.table("contract_events").insert({
                "contract_id": contract_id,
                "event_type":  "completed",
            }).execute()
        except Exception:
            pass

        # Notifica TODAS as partes que o contrato foi concluído (licenciamento efetivado).
        # Inclui: comprador, vendedor, coautores e — em contratos trilaterais —
        # a editora terceira ou a editora-mãe (agregadora).
        try:
            from services.notificacoes import notify as _notify
            ctr = sb.table("contracts").select("obra_id, buyer_id, seller_id, valor_cents").eq("id", contract_id).single().execute().data or {}
            obra2 = sb.table("obras").select("nome").eq("id", ctr.get("obra_id")).single().execute().data or {}
            obra_nome2 = obra2.get("nome") or "obra"

            # Reúne IDs únicos: buyer, seller + todos os signers
            partes_ids = set(filter(None, [ctr.get("buyer_id"), ctr.get("seller_id")]))
            try:
                signers_rows = sb.table("contract_signers").select("user_id").eq("contract_id", contract_id).execute().data or []
                for r in signers_rows:
                    if r.get("user_id"):
                        partes_ids.add(r["user_id"])
            except Exception:
                pass

            for pid in partes_ids:
                _notify(
                    pid,
                    tipo="licenciamento",
                    titulo="Contrato concluído",
                    mensagem=f'O licenciamento da obra "{obra_nome2}" foi finalizado: todas as partes assinaram.',
                    link=f"/contratos/licenciamento/{contract_id}",
                    payload={"contract_id": contract_id, "obra_id": ctr.get("obra_id")},
                )
        except Exception:
            pass

        # Se for trilateral (oferta editora terceira), captura o pagamento.
        try:
            c = sb.table("contracts").select("trilateral, oferta_id").eq("id", contract_id).single().execute().data
            if c and c.get("trilateral") and c.get("oferta_id"):
                from services.ofertas_terceiros import on_contrato_concluido
                on_contrato_concluido(contract_id)
        except Exception:
            pass

    return {"todos_assinaram": bool(todos)}
