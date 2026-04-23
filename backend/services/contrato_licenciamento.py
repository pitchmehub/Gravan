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

CLÁUSULA 2 — CESSÃO DE DIREITOS

O(s) AUTOR(ES) autoriza(m), de forma irrevogável e irretratável, o LICENCIADO a:
I. Reproduzir a obra em qualquer formato ou suporte;
II. Distribuir e comercializar a obra em meios físicos e digitais;
III. Disponibilizar a obra em plataformas de streaming, incluindo, mas não se limitando a Spotify e Apple Music;
IV. Utilizar a obra em redes sociais e plataformas digitais;
V. Sincronizar a obra com conteúdos audiovisuais.

CLÁUSULA 3 — TERRITÓRIO E PRAZO

A presente autorização é concedida:
- Em caráter mundial;
- Pelo prazo integral de proteção legal dos direitos autorais, conforme a Lei nº 9.610/98;
sendo considerada definitiva, irrevogável e irretratável.

CLÁUSULA 4 — GARANTIA DE TITULARIDADE

O(s) AUTOR(ES) declara(m) que:
I. São legítimos titulares da obra;
II. A obra é original e não infringe direitos de terceiros;
III. Assumem total responsabilidade por eventuais reivindicações.

O LICENCIADO fica isento de qualquer responsabilidade perante terceiros.

CLÁUSULA 5 — REMUNERAÇÃO

5.1 — BUYOUT (VENDA DA COMPOSIÇÃO)

O LICENCIADO pagará ao(s) AUTOR(ES) o valor de {{valor_buyout_extenso}} referente à aquisição da composição por meio da plataforma PITCH.ME.

5.2 — ROYALTIES AUTORAIS (EXECUÇÃO PÚBLICA)

Os rendimentos provenientes de execução pública arrecadados pelo ECAD serão distribuídos da seguinte forma:
- 80% (oitenta por cento) para o(s) AUTOR(ES) e coautores;
- 10% (dez por cento) para o INTÉRPRETE;
- 10% (dez por cento) para a EDITORA PITCH.ME.

5.3 — ROYALTIES DE FONOGRAMA

O(s) AUTOR(ES) fará(ão) jus a 2% (dois por cento) sobre a receita do fonograma. Forma de pagamento: diretamente pela distribuidora digital do LICENCIADO.

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

CLÁUSULA 8 — IRREVOGABILIDADE

Este contrato é celebrado em caráter irrevogável e irretratável, não podendo ser rescindido unilateralmente.

CLÁUSULA 9 — DISPOSIÇÕES GERAIS

I. Este contrato obriga as partes e seus sucessores;
II. Pode ser firmado digitalmente, nos termos da MP nº 2.200-2/2001 e Lei nº 14.063/2020;
III. Integra as regras da plataforma PITCH.ME.

CLÁUSULA 10 — DIVISÃO DE DIREITOS ENTRE COAUTORES (SPLIT)

Fica estabelecido que a divisão dos direitos autorais entre os coautores é a seguinte:
{{split_lista}}

Parágrafo Primeiro: A divisão acima foi declarada pelos próprios autores na plataforma PITCH.ME no momento do cadastro da obra.

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

    conteudo = (TEMPLATE_LICENCIAMENTO
        .replace("{{autores_bloco}}",          "\n".join(autores_bloco_partes).strip())
        .replace("{{interprete_nome}}",        buyer.get("nome_completo") or buyer.get("nome") or "—")
        .replace("{{interprete_cpf}}",         _decrypt(buyer.get("cpf","")) or "Não informado")
        .replace("{{interprete_endereco}}",    _endereco(buyer))
        .replace("{{interprete_cidade_uf}}",   _cidade_uf(buyer))
        .replace("{{obra_nome}}",              obra.get("nome","—"))
        .replace("{{valor_buyout_extenso}}",   _moeda(tx["valor_cents"]))
        .replace("{{autores_nomes_artisticos}}", ", ".join(autores_nomes_artisticos))
        .replace("{{isrc}}",                   obra.get("isrc") or "a definir após lançamento")
        .replace("{{iswc}}",                   obra.get("iswc") or "a definir após lançamento")
        .replace("{{split_lista}}",            "\n".join(split_lista_partes))
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


TEMPLATE_TRILATERAL = """CONTRATO TRILATERAL DE LICENCIAMENTO DE OBRA MUSICAL
EDITADA POR TERCEIRA EDITORA

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
PITCH.ME EDITORA MUSICAL LTDA., CNPJ 64.342.514/0001-08, sediada na cidade
do Rio de Janeiro/RJ, doravante "PITCH.ME".

LICENCIADO (INTÉRPRETE/PRODUTOR):
Nome/Razão Social: {{interprete_nome}}
CPF/CNPJ: {{interprete_cpf}}
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
da PITCH.ME como plataforma intermediária.

CLÁUSULA 3 — VALOR E ESCROW

O LICENCIADO pagará pelo licenciamento o valor de {{valor_buyout_extenso}},
retido em escrow pela PITCH.ME até a assinatura eletrônica de todas as partes.
A liberação do valor ocorre após a assinatura final, sendo distribuído conforme
contratos prévios entre AUTOR(ES) e EDITORA TERCEIRA.

CLÁUSULA 4 — DECLARAÇÃO DA EDITORA TERCEIRA

A EDITORA TERCEIRA declara: (i) possuir contrato de edição em vigor sobre a
obra; (ii) ter ciência e concordância com o presente licenciamento;
(iii) responsabilizar-se pela distribuição dos valores cabíveis ao(s)
AUTOR(ES) nos termos do contrato de edição existente entre as partes.

CLÁUSULA 5 — TERRITÓRIO E PRAZO

Autorização mundial, pelo prazo integral de proteção dos direitos autorais
(Lei 9.610/98), em caráter definitivo, irrevogável e irretratável.

CLÁUSULA 6 — ROYALTIES (ECAD)

Os rendimentos provenientes de execução pública arrecadados pelo ECAD serão
distribuídos conforme cadastro junto ao órgão, observando-se a divisão entre
AUTOR(ES) e EDITORA TERCEIRA já registrada e a participação do INTÉRPRETE
nos termos legais.

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
    Gera o contrato trilateral (autor + editora terceira + Pitch.me + comprador)
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

    conteudo = (TEMPLATE_TRILATERAL
        .replace("{{autores_bloco}}",          "\n".join(autores_bloco).strip())
        .replace("{{editora_razao}}",          editora_t.get("razao_social") or of["editora_terceira_nome"])
        .replace("{{editora_cnpj}}",           cnpj_dec)
        .replace("{{editora_responsavel}}",    editora_t.get("responsavel_nome") or "—")
        .replace("{{editora_email}}",          editora_t.get("email") or of["editora_terceira_email"])
        .replace("{{editora_endereco}}",       editora_endereco)
        .replace("{{interprete_nome}}",        buyer.get("nome_completo") or buyer.get("nome") or "—")
        .replace("{{interprete_cpf}}",         _decrypt(buyer.get("cpf","")) or "Não informado")
        .replace("{{interprete_endereco}}",    _endereco(buyer))
        .replace("{{interprete_cidade_uf}}",   _cidade_uf(buyer))
        .replace("{{obra_nome}}",              obra.get("nome", "—"))
        .replace("{{valor_buyout_extenso}}",   _moeda(of["valor_cents"]))
        .replace("{{split_lista}}",            "\n".join(split_lista))
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

        # Se for trilateral (oferta editora terceira), captura o pagamento.
        try:
            c = sb.table("contracts").select("trilateral, oferta_id").eq("id", contract_id).single().execute().data
            if c and c.get("trilateral") and c.get("oferta_id"):
                from services.ofertas_terceiros import on_contrato_concluido
                on_contrato_concluido(contract_id)
        except Exception:
            pass

    return {"todos_assinaram": bool(todos)}
