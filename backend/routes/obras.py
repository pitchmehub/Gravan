"""Routes: /api/obras

CORREÇÕES DE VULNERABILIDADES:
- #12 (MÉDIA): IP hashing para LGPD compliance
- #14 (MÉDIA): Audit logging
"""
import json
from datetime import datetime
from flask import Blueprint, request, jsonify, g, abort
from middleware.auth import require_auth
from services.obras import ObraService
from db.supabase_client import get_supabase
from utils.crypto import hash_ip, decrypt_pii

obras_bp = Blueprint("obras", __name__)


def _get_perfil():
    sb = get_supabase()
    r = sb.table("perfis").select("*").eq("id", g.user.id).single().execute()
    return r.data if r.data else None


@obras_bp.route("", methods=["POST"])
@obras_bp.route("/", methods=["POST"])
@require_auth
def criar_obra():
    perfil = _get_perfil()
    if not perfil:
        abort(404, description="Perfil não encontrado.")
    if perfil.get("role") not in ("compositor", "administrador"):
        abort(403, description="Apenas compositores podem cadastrar obras.")
    if not perfil.get("cadastro_completo"):
        abort(422, description="Você precisa completar seu cadastro (CPF, RG e endereço) antes de publicar uma obra.")

    if "audio" not in request.files:
        abort(422, description="Campo 'audio' é obrigatório.")
    audio_file = request.files["audio"]
    if not audio_file.filename.lower().endswith(".mp3"):
        abort(422, description="Apenas arquivos .mp3 são aceitos.")

    audio_bytes = audio_file.read()

    nome  = request.form.get("nome", "").strip()
    letra = request.form.get("letra", "").strip()
    if not nome or not letra:
        abort(422, description="Campos 'nome' e 'letra' são obrigatórios.")

    GENEROS_PERMITIDOS = {
        "Sertanejo", "MPB", "Funk", "Samba", "Rock", "Pop",
        "Gospel", "Forró", "Pagode", "RNB", "RAP", "OUTROS",
    }
    genero = (request.form.get("genero") or "").strip()
    if not genero:
        abort(422, description="Campo 'genero' é obrigatório.")
    if genero not in GENEROS_PERMITIDOS:
        abort(422, description=(
            "Gênero inválido. Valores permitidos: "
            + ", ".join(sorted(GENEROS_PERMITIDOS))
        ))

    try:
        preco_cents = int(request.form.get("preco_cents", 0))
        if preco_cents < 100: raise ValueError()
    except (ValueError, TypeError):
        abort(422, description="'preco_cents' deve ser inteiro >= 100.")

    # ── Faixa de preço por plano ────────────────────────────────────
    # STARTER (grátis):  R$ 500 a R$ 1.000
    # PRO (assinante):   R$ 500 a R$ 10.000
    PRECO_MIN_CENTS = 50_000     # R$ 500,00
    PRECO_MAX_STARTER = 100_000  # R$ 1.000,00
    PRECO_MAX_PRO = 1_000_000    # R$ 10.000,00

    plano_titular = (perfil.get("plano") or "STARTER").upper()
    status_ass = perfil.get("status_assinatura") or "inativa"
    is_pro_titular = plano_titular == "PRO" and status_ass in ("ativa", "cancelada", "past_due")

    if preco_cents < PRECO_MIN_CENTS:
        abort(422, description="Valor mínimo da obra é R$ 500,00.")

    if is_pro_titular:
        if preco_cents > PRECO_MAX_PRO:
            abort(422, description="Valor máximo da obra (PRO) é R$ 10.000,00.")
    else:
        if preco_cents > PRECO_MAX_STARTER:
            abort(
                402,
                description=(
                    "Para precificar obras acima de R$ 1.000, assine o plano "
                    "PRO e tenha acesso a compradores de alto valor."
                ),
            )

    try:
        coautorias = json.loads(request.form.get("coautorias", "[]"))
        if not isinstance(coautorias, list): raise ValueError()
    except (ValueError, json.JSONDecodeError):
        abort(422, description="'coautorias' deve ser array JSON válido.")

    termos_aceitos = request.form.get("termos_aceitos", "false").lower() == "true"
    if not termos_aceitos:
        abort(422, description="Você precisa aceitar os Termos de Uso.")

    obra_editada = request.form.get("obra_editada", "false").lower() == "true"

    # Dados da editora terceira (somente quando obra_editada=true)
    editora_terceira_nome     = (request.form.get("editora_terceira_nome") or "").strip()
    editora_terceira_email    = (request.form.get("editora_terceira_email") or "").strip().lower()
    editora_terceira_telefone = (request.form.get("editora_terceira_telefone") or "").strip()
    editora_terceira_id       = None  # vai ser preenchido se já existir editora cadastrada

    if obra_editada:
        if not editora_terceira_nome or not editora_terceira_email:
            abort(422, description="Para obras já editadas, informe nome e e-mail da editora terceira.")
        import re as _re_em
        if not _re_em.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", editora_terceira_email):
            abort(422, description="E-mail da editora terceira inválido.")

        # ── LOOKUP: a editora já tem cadastro na plataforma? ──
        sb = get_supabase()
        ex = (sb.table("perfis")
                .select("id, razao_social, nome_fantasia")
                .eq("email", editora_terceira_email)
                .eq("role", "publisher")
                .limit(1)
                .execute())
        if ex.data:
            editora_terceira_id = ex.data[0]["id"]
            # Usa razão social oficial em vez do que foi digitado, se disponível
            nome_oficial = (ex.data[0].get("razao_social")
                            or ex.data[0].get("nome_fantasia"))
            if nome_oficial:
                editora_terceira_nome = nome_oficial

    # Para obras editadas por terceiros NÃO exigimos contrato_aceito
    contrato_aceito = request.form.get("contrato_aceito", "false").lower() == "true"
    if not obra_editada and not contrato_aceito:
        abort(422, description="Você precisa assinar o Contrato de Edição para prosseguir.")

    service = ObraService()
    obra = service.criar_obra(
        titular_id=g.user.id,
        nome=nome, letra=letra, genero=genero,
        preco_cents=preco_cents,
        audio_bytes=audio_bytes,
        coautorias=coautorias,
        termos_aceitos=termos_aceitos,
        obra_editada_terceiros=obra_editada,
        editora_terceira_nome=editora_terceira_nome,
        editora_terceira_email=editora_terceira_email,
        editora_terceira_telefone=editora_terceira_telefone,
        editora_terceira_id=editora_terceira_id,
    )

    # IA grátis: gera capa via Pollinations.ai (apenas URL, sem download)
    try:
        from services.ai_capa import gerar_e_salvar_capa
        import secrets as _sec
        capa_url = gerar_e_salvar_capa(
            obra_id=obra["id"],
            nome=obra.get("nome") or nome,
            genero=obra.get("genero") or genero,
            seed=_sec.randbelow(10_000_000),
        )
        if capa_url:
            obra["cover_url"] = capa_url
    except Exception as _e:
        print(f"[obras] geração de capa falhou: {_e}")

    sb = get_supabase()

    # Obra editada por terceiros: NÃO geramos contrato de edição com a Gravan.
    if obra_editada:
        try:
            from utils.audit import log_event
            log_event("obra.criada", entity_type="obra", entity_id=obra["id"],
                      metadata={"titulo": obra.get("nome"),
                                "editada_terceiros": True,
                                "editora_terceira_nome": editora_terceira_nome,
                                "editora_terceira_email": editora_terceira_email,
                                "editora_terceira_id": editora_terceira_id,
                                "editora_ja_cadastrada": editora_terceira_id is not None})
        except Exception:
            pass

        if editora_terceira_id:
            # Vincula a obra à editora na tabela obras
            try:
                sb.table("obras").update({"publisher_id": editora_terceira_id}).eq("id", obra["id"]).execute()
            except Exception as e:
                print(f"[obras] falha ao vincular publisher_id: {e}")

            # Gera o contrato bilateral AUTOR ↔ EDITORA
            contrato_gerado = None
            try:
                from services.contrato_publisher import gerar_contrato_edicao
                contrato_gerado = gerar_contrato_edicao(obra["id"], g.user.id, editora_terceira_id)
            except Exception as e:
                print(f"[obras] falha ao gerar contrato de edição (terceiros): {e}")

            # Notifica a EDITORA: contrato gerado, aguarda assinatura dela
            try:
                from services.notificacoes import notify
                _cid_edit = (contrato_gerado or {}).get("id")
                notify(
                    perfil_id=editora_terceira_id,
                    tipo="contrato_edicao_gerado",
                    titulo="Novo Contrato de Edição Musical aguarda sua assinatura",
                    mensagem=(
                        f"Um Contrato de Edição Musical bilateral foi gerado para a obra "
                        f"\"{obra.get('nome')}\", cadastrada pelo compositor. "
                        f"Acesse seus contratos para ler e assinar."
                    ),
                    link=f"/contratos?contrato={_cid_edit}" if _cid_edit else "/contratos",
                    payload={"obra_id": obra["id"], "contrato_id": _cid_edit, "tipo": "edicao", "via": "contrato_bilateral"},
                )
            except Exception as e:
                print(f"[obras] notify editora contrato falhou: {e}")

            # Notifica o ARTISTA: contrato gerado, aguarda assinatura dele também
            try:
                from services.notificacoes import notify
                notify(
                    perfil_id=g.user.id,
                    tipo="contrato_edicao_gerado",
                    titulo="Contrato de Edição Musical gerado — assine agora",
                    mensagem=(
                        f"Sua obra \"{obra.get('nome')}\" está vinculada à sua editora. "
                        f"Um Contrato de Edição Musical bilateral foi gerado entre você e sua editora. "
                        f"Acesse \"Meus Contratos\" para ler e assinar."
                    ),
                    link=f"/contratos?contrato={_cid_edit}" if _cid_edit else "/contratos",
                    payload={"obra_id": obra["id"], "contrato_id": _cid_edit, "tipo": "edicao", "via": "contrato_bilateral"},
                )
            except Exception as e:
                print(f"[obras] notify artista contrato falhou: {e}")

        return jsonify(obra), 201

    # Gera e assina o contrato de edição (fluxo padrão da Gravan)
    def _lc(key, default=""):
        try:
            r = sb.table("landing_content").select("valor").eq("id", key).single().execute()
            return (r.data or {}).get("valor", default)
        except Exception:
            return default

    tpl_texto       = _lc("contrato_edicao_template", "")
    editora_dados   = _lc(
        "contrato_edicao_editora_dados",
        "GRAVAN EDITORA MUSICAL LTDA., inscrita no CNPJ/MF sob o nº 64.342.514/0001-08, com sede na Cidade do Rio de Janeiro, Estado do Rio de Janeiro"
    )
    contrato_versao = _lc("contrato_edicao_versao", "v2.0")
    plataforma_razao = editora_dados.split(",")[0].strip() if editora_dados else "GRAVAN EDITORA MUSICAL LTDA."
    plataforma_cnpj = "64.342.514/0001-08"
    plataforma_endereco = "Rio de Janeiro - RJ"
    import re as _re
    m_cnpj = _re.search(r"CNPJ[^\d]*([\d./-]+)", editora_dados)
    if m_cnpj:
        plataforma_cnpj = m_cnpj.group(1).strip()
    m_sede = _re.search(r"sede\s+(?:na|em)\s+(.+)$", editora_dados, _re.IGNORECASE)
    if m_sede:
        plataforma_endereco = m_sede.group(1).strip().rstrip(".")

    endereco = ", ".join(filter(None, [
        perfil.get("endereco_rua"),
        perfil.get("endereco_numero"),
        perfil.get("endereco_compl"),
        perfil.get("endereco_bairro"),
        perfil.get("endereco_cidade"),
        perfil.get("endereco_uf"),
        f"CEP {perfil['endereco_cep']}" if perfil.get("endereco_cep") else None,
    ]))
    agora_str = datetime.utcnow().strftime("%d/%m/%Y às %H:%M UTC")

    cpf_decrypted = decrypt_pii(perfil.get("cpf", ""))
    rg_decrypted = decrypt_pii(perfil.get("rg", ""))

    share_autor = 100.0
    coautores_str = "autoria única"
    try:
        titular_entry = next((c for c in coautorias if c["perfil_id"] == g.user.id), None)
        if titular_entry:
            share_autor = float(titular_entry.get("share_pct", 100))
        outros_ids = [c["perfil_id"] for c in coautorias if c["perfil_id"] != g.user.id]
        if outros_ids:
            outros = sb.table("perfis").select("id, nome_completo, nome").in_("id", outros_ids).execute()
            mapa = {p["id"]: (p.get("nome_completo") or p.get("nome") or "Coautor") for p in (outros.data or [])}
            partes = []
            for c in coautorias:
                if c["perfil_id"] == g.user.id: continue
                nm = mapa.get(c["perfil_id"], "Coautor")
                partes.append(f"{nm} ({float(c['share_pct']):.2f}%)")
            coautores_str = "; ".join(partes) if partes else "autoria única"
    except Exception:
        pass

    conteudo = (tpl_texto
        .replace("{{nome_completo}}", perfil.get("nome_completo") or perfil.get("nome") or "")
        .replace("{{cpf}}",            cpf_decrypted or "")
        .replace("{{rg}}",             rg_decrypted or "")
        .replace("{{endereco_completo}}", endereco or "Não informado")
        .replace("{{email}}",          perfil.get("email") or "")
        .replace("{{data_assinatura}}", agora_str)
        .replace("{{obra_nome}}",       nome)
        .replace("{{obra_letra}}",      (letra or "").strip() or "—")
        .replace("{{share_autor_pct}}", f"{share_autor:.2f}".rstrip("0").rstrip("."))
        .replace("{{coautores_lista}}", coautores_str)
        .replace("{{plataforma_razao_social}}", plataforma_razao)
        .replace("{{plataforma_cnpj}}",         plataforma_cnpj)
        .replace("{{plataforma_endereco}}",     plataforma_endereco)
    )

    ip_hashed = hash_ip(request.remote_addr)
    import hashlib as _hashlib
    conteudo_hash = _hashlib.sha256(conteudo.encode("utf-8")).hexdigest()

    contrato_row = {
        "obra_id":       obra["id"],
        "titular_id":    g.user.id,
        "conteudo":      conteudo,
        "ip_assinatura": ip_hashed,
        "dados_titular": {
            "nome_completo":  perfil.get("nome_completo"),
            "cpf":            cpf_decrypted,
            "rg":             rg_decrypted,
            "endereco":       endereco,
            "email":          perfil.get("email"),
            "share_pct":      share_autor,
            "coautores":      coautores_str,
            "conteudo_hash":  conteudo_hash,
        },
    }
    try:
        contrato = sb.table("contratos_edicao").insert({**contrato_row, "versao": contrato_versao}).execute()
    except Exception:
        contrato = sb.table("contratos_edicao").insert(contrato_row).execute()

    if contrato.data:
        sb.table("obras").update({
            "contrato_edicao_id": contrato.data[0]["id"],
        }).eq("id", obra["id"]).execute()

    # ── Gravan Editora Operacional ────────────────────────────────
    # Vincula a obra à Gravan como Editora Detentora dos Direitos e
    # gera o contrato de edição auto-aceito (contracts_edicao).
    # Apenas para autores sem editora parceira já vinculada.
    publisher_do_autor = perfil.get("publisher_id")
    if not publisher_do_autor:
        try:
            from services.gravan_editora import (
                vincular_obra_gravan_editora,
                gerar_contrato_gravan_editora,
            )
            vincular_obra_gravan_editora(obra["id"])
            gerar_contrato_gravan_editora(
                obra_id    = obra["id"],
                autor_id   = g.user.id,
                perfil     = perfil,
                obra_nome  = nome,
                obra_letra = letra,
                coautorias = coautorias,
                ip_hashed  = ip_hashed,
                versao     = contrato_versao,
            )
        except Exception as _ge:
            print(f"[obras] falha ao vincular Gravan Editora Operacional: {_ge}")

    try:
        from utils.audit import log_event
        log_event("obra.criada", entity_type="obra", entity_id=obra["id"],
                  metadata={"titulo": obra.get("titulo") or obra.get("nome"),
                            "managed_by_publisher": not bool(publisher_do_autor),
                            "gravan_editora_operacional": not bool(publisher_do_autor)})
    except Exception:
        pass

    # Se o autor é AGREGADO de uma editora (perfil.publisher_id setado),
    # vincula a obra à editora e gera o contrato de edição autor↔editora.
    # Sem isso, o dashboard da editora nunca mostrava as obras dos agregados.
    if publisher_do_autor:
        try:
            sb.table("obras").update({"publisher_id": publisher_do_autor}).eq("id", obra["id"]).execute()
        except Exception as e:
            print(f"[obras] falha ao vincular publisher_id (agregado): {e}")
        try:
            from services.contrato_publisher import gerar_contrato_edicao
            gerar_contrato_edicao(obra["id"], g.user.id, publisher_do_autor)
        except Exception as e:
            print(f"[obras] falha ao gerar contrato de edição (agregado): {e}")
        try:
            from services.notificacoes import notify
            notify(
                perfil_id=publisher_do_autor,
                tipo="obra_cadastrada",
                titulo="Novo contrato de edição disponível",
                mensagem=(
                    f"Seu agregado cadastrou a obra \"{obra.get('nome')}\". "
                    f"Um contrato de edição foi gerado e está aguardando sua assinatura."
                ),
                link="/contratos",
                payload={"obra_id": obra["id"], "via": "agregado"},
            )
        except Exception as e:
            print(f"[obras] notify agregado falhou: {e}")

    return jsonify(obra), 201


@obras_bp.route("/<obra_id>", methods=["DELETE"])
@require_auth
def excluir_obra(obra_id):
    sb = get_supabase()
    obra = sb.table("obras").select("id, titular_id, audio_path").eq("id", obra_id).single().execute()
    if not obra.data:
        abort(404, description="Obra não encontrada.")
    perfil = _get_perfil()
    if obra.data["titular_id"] != g.user.id and perfil.get("role") != "administrador":
        abort(403, description="Apenas o titular pode excluir esta obra.")

    if obra.data.get("audio_path"):
        try: sb.storage.from_("obras-audio").remove([obra.data["audio_path"]])
        except Exception: pass

    sb.table("obras").delete().eq("id", obra_id).execute()
    return jsonify({"ok": True}), 200


@obras_bp.route("/minhas", methods=["GET"])
@require_auth
def minhas_obras():
    service = ObraService()
    obras = service.obras_do_compositor(perfil_id=g.user.id)
    return jsonify(obras), 200


@obras_bp.route("/catalogo", methods=["GET"])
def catalogo_publico():
    genero   = request.args.get("genero")
    page     = max(1, int(request.args.get("page", 1)))
    per_page = min(50, int(request.args.get("per_page", 20)))
    service  = ObraService()
    return jsonify(service.catalogo_publico(genero=genero, page=page, per_page=per_page)), 200


@obras_bp.route("/<obra_id>/preview-url", methods=["GET"])
@require_auth
def preview_url(obra_id):
    sb = get_supabase()
    obra = sb.table("obras").select("audio_path").eq("id", obra_id).single().execute()
    if not obra.data or not obra.data.get("audio_path"):
        abort(404, description="Áudio não encontrado.")
    signed = sb.storage.from_("obras-audio").create_signed_url(obra.data["audio_path"], 3600)
    return jsonify({"url": signed.get("signedURL") or signed.get("signedUrl")}), 200
