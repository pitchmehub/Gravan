"""
Rotas para gerenciar AGREGADOS de uma editora.

Fluxos:
  • CADASTRAR  (modo=cadastrar): editora cria perfil novo (ghost user) + termo
                                 + envia e-mail de convite. Vínculo só fica
                                 firme quando o artista define senha e aceita
                                 o termo no primeiro login.
  • ADICIONAR  (modo=adicionar): editora informa apenas o e-mail. Sistema
                                 cria convite vinculado ao perfil existente,
                                 envia notificação + e-mail. Artista aceita
                                 ou recusa via tela `/convites`.

Endpoints:
  GET    /api/agregados                          → lista artistas vinculados
  POST   /api/agregados/cadastrar                → cria ghost + convite
  POST   /api/agregados/adicionar                → cria convite p/ artista existente
  GET    /api/agregados/convites                 → convites enviados pela editora
  DELETE /api/agregados/convites/<cid>           → cancela convite pendente
  GET    /api/agregados/convites/recebidos       → convites recebidos pelo artista
  GET    /api/agregados/convites/<cid>/termo     → HTML do termo (qualquer parte)
  POST   /api/agregados/convites/<cid>/aceitar   → artista aceita
  POST   /api/agregados/convites/<cid>/recusar   → artista recusa
  GET    /api/agregados/<aid>                    → detalhes (editora)
  DELETE /api/agregados/<aid>                    → desvincula
  GET    /api/agregados/<aid>/dashboard          → dashboard do agregado
"""
import secrets
from datetime import datetime, timezone

from flask import Blueprint, request, jsonify, g, abort

from middleware.auth import require_auth
from db.supabase_client import get_supabase
from utils.audit import log_event
from utils.crypto import encrypt_pii, decrypt_pii
from utils.termo_agregado import gerar_termo_html, gerar_termo_text, VERSAO_ATUAL, _mask_cpf
from services.notificacoes import notify
from services.email_service import send_email, _wrap_html

agregados_bp = Blueprint("agregados", __name__, url_prefix="/api/agregados")


# ──────────────── helpers ────────────────

def _ensure_publisher(sb):
    me = sb.table("perfis").select("*").eq("id", g.user.id).single().execute()
    if not me.data or me.data.get("role") != "publisher":
        return None
    return me.data


def _editora_para_termo(perfil_editora: dict) -> dict:
    """Decripta CNPJ e CPF do responsável (se possível) para uso no termo."""
    out = dict(perfil_editora)
    for orig, dest in (("cnpj", "cnpj_display"),
                       ("responsavel_cpf", "responsavel_cpf_display")):
        v = perfil_editora.get(orig)
        if v:
            try:
                out[dest] = decrypt_pii(v)
            except Exception:
                out[dest] = ""
    return out


def _artista_para_termo(perfil_artista: dict) -> dict:
    """Decripta CPF/RG do artista (se possível) para uso no termo."""
    out = dict(perfil_artista or {})
    for orig, dest in (("cpf", "cpf_display"), ("rg", "rg_display")):
        v = (perfil_artista or {}).get(orig)
        if v:
            try:
                out[dest] = decrypt_pii(v)
            except Exception:
                out[dest] = ""
    return out


def _carregar_perfil_completo(sb, perfil_id: str) -> dict | None:
    """Busca o perfil completo (incl. PII e endereço) para gerar/re-gerar termo."""
    if not perfil_id:
        return None
    r = sb.table("perfis").select(
        "id,email,nome_completo,nome_artistico,cpf,rg,"
        "endereco_rua,endereco_numero,endereco_compl,endereco_bairro,"
        "endereco_cidade,endereco_uf,endereco_cep,publisher_id,is_ghost,role"
    ).eq("id", perfil_id).maybe_single().execute()
    return r.data if r else None


def _client_ip() -> str:
    return request.headers.get("X-Forwarded-For", request.remote_addr or "").split(",")[0].strip()


def _frontend_url(path: str = "") -> str:
    """Monta uma URL absoluta para a notificação/e-mail."""
    import os
    base = os.environ.get("FRONTEND_URL") or os.environ.get("PUBLIC_URL") or ""
    if not base:
        # tenta REPLIT_DEV_DOMAIN
        rd = os.environ.get("REPLIT_DEV_DOMAIN")
        if rd:
            base = f"https://{rd}"
    return f"{base.rstrip('/')}{path}" if base else path


# ──────────────── listagem ────────────────

@agregados_bp.get("")
@require_auth
def listar():
    sb = get_supabase()
    if not _ensure_publisher(sb):
        abort(403, description="Apenas editoras")

    r = sb.table("perfis").select(
        "id,nome_completo,nome_artistico,email,is_ghost,agregado_desde"
    ).eq("publisher_id", g.user.id).order("agregado_desde", desc=True).execute()

    return jsonify(r.data or [])


# ──────────────── CADASTRAR (cria ghost + termo) ────────────────

@agregados_bp.post("/cadastrar")
@require_auth
def cadastrar_agregado():
    """
    Body: { nome_completo, nome_artistico, rg, cpf, email,
            endereco_*, responsavel_aceite (str — nome do responsável que aceita o termo) }

    Lógica:
      1. Procura perfil por email
         - Se já existir, retorna 409 e orienta a usar /adicionar
      2. Cria ghost user (auth + perfil) com is_ghost=true
      3. Gera termo jurídico, cria convite (modo=cadastrar)
      4. Manda e-mail ao artista com link de definir senha + ler/aceitar termo
    """
    data = request.get_json(silent=True) or {}
    obrigatorios = ["nome_completo", "nome_artistico", "rg", "cpf", "email",
                    "responsavel_aceite", "responsavel_cpf"]
    faltam = [c for c in obrigatorios if not (data.get(c) or "").strip()]
    if faltam:
        abort(400, description=f"Campos obrigatórios faltando: {', '.join(faltam)}")

    import re as _re
    resp_cpf_digits = _re.sub(r"\D", "", data.get("responsavel_cpf") or "")
    if len(resp_cpf_digits) != 11:
        abort(422, description="CPF do solicitante inválido (11 dígitos).")

    sb = get_supabase()
    editora = _ensure_publisher(sb)
    if not editora:
        abort(403, description="Apenas editoras")

    email = data["email"].strip().lower()

    existing = sb.table("perfis").select("id,publisher_id,is_ghost,nome_completo")\
                 .eq("email", email).maybe_single().execute()
    if existing and existing.data:
        abort(409, description='Já existe perfil com esse e-mail. Use "Adicionar agregado" para enviar um convite.')

    # 1. Cria ghost auth
    senha_temp = secrets.token_urlsafe(24)
    invite_token = secrets.token_urlsafe(32)
    try:
        novo_auth = sb.auth.admin.create_user({
            "email":         email,
            "password":      senha_temp,
            "email_confirm": False,
            "user_metadata": {"ghost": True, "publisher_id": g.user.id},
        })
        novo_id = novo_auth.user.id
    except Exception as e:
        abort(400, description=f"Não foi possível criar usuário: {e}")

    # 2. Insere perfil (publisher_id NULL ainda — só vincula no aceite)
    perfil_payload = {
        "id":               novo_id,
        "email":            email,
        "nome_completo":    data["nome_completo"].strip(),
        "nome_artistico":   data["nome_artistico"].strip(),
        "rg":               encrypt_pii(data["rg"].strip()),
        "cpf":              encrypt_pii(data["cpf"].strip()),
        "endereco_rua":     (data.get("endereco_rua") or "").strip(),
        "endereco_numero":  (data.get("endereco_numero") or "").strip(),
        "endereco_compl":   (data.get("endereco_compl") or "").strip(),
        "endereco_bairro":  (data.get("endereco_bairro") or "").strip(),
        "endereco_cidade":  (data.get("endereco_cidade") or "").strip(),
        "endereco_uf":      (data.get("endereco_uf") or "").strip().upper()[:2],
        "endereco_cep":     (data.get("endereco_cep") or "").strip(),
        "role":             "artist",
        "is_ghost":         True,
        "ghost_invite_token":   invite_token,
        "ghost_invite_sent_at": datetime.now(timezone.utc).isoformat(),
    }
    sb.table("perfis").insert(perfil_payload).execute()

    # 3. Gera termo e cria convite — usa dados REAIS recém-cadastrados pela editora
    artista_termo = {
        "nome_completo":   perfil_payload["nome_completo"],
        "nome_artistico":  perfil_payload["nome_artistico"],
        "cpf_display":     data["cpf"].strip(),
        "rg_display":      data["rg"].strip(),
        "endereco_rua":    perfil_payload.get("endereco_rua"),
        "endereco_numero": perfil_payload.get("endereco_numero"),
        "endereco_compl":  perfil_payload.get("endereco_compl"),
        "endereco_bairro": perfil_payload.get("endereco_bairro"),
        "endereco_cidade": perfil_payload.get("endereco_cidade"),
        "endereco_uf":     perfil_payload.get("endereco_uf"),
        "endereco_cep":    perfil_payload.get("endereco_cep"),
    }
    termo_html = gerar_termo_html(
        editora=_editora_para_termo(editora),
        artista=artista_termo,
        email_artista=email,
        modo="cadastrar",
    )

    convite_payload = {
        "editora_id":   g.user.id,
        "artista_id":   novo_id,
        "email_artista": email,
        "modo":         "cadastrar",
        "status":       "pendente",
        "termo_html":   termo_html,
        "termo_versao": VERSAO_ATUAL,
        "responsavel_editora_nome":     data["responsavel_aceite"].strip(),
        "responsavel_editora_cpf_mask": _mask_cpf(resp_cpf_digits),
        "editora_aceito_ip":            _client_ip(),
    }
    convite = sb.table("agregado_convites").insert(convite_payload).execute()
    cid = (convite.data or [{}])[0].get("id")

    # 4. E-mail
    link = _frontend_url(f"/ativar?token={invite_token}")
    body = f"""
      <h2 style="margin:0 0 8px">Você foi convidado(a) para a Gravan</h2>
      <p style="color:#444;font-size:14px">
        A editora <strong>{(editora.get('razao_social') or editora.get('nome_completo') or 'Editora')}</strong>
        cadastrou um perfil em seu nome na plataforma Gravan e está te convidando para
        agregar suas obras ao catálogo dela.
      </p>
      <p style="color:#444;font-size:14px">
        Clique no botão abaixo para escolher sua senha. No primeiro acesso você
        poderá <strong>ler e aceitar (ou recusar) o termo de agregação</strong> antes que o
        vínculo seja efetivado. Sem o seu aceite, nenhuma obra será administrada
        em seu nome.
      </p>
      <div style="text-align:center;margin:24px 0">
        <a href="{link}" style="display:inline-block;padding:14px 28px;
           background:#BE123C;color:#fff;text-decoration:none;
           border-radius:10px;font-weight:700">Ativar minha conta</a>
      </div>
      <p style="color:#666;font-size:12px">
        Se você não conhece essa editora ou não esperava esse convite,
        pode simplesmente ignorar este e-mail — nenhum dado seu será cedido sem sua autorização.
      </p>
    """
    try:
        send_email(email, "Convite Gravan — defina sua senha e responda ao convite",
                   _wrap_html("Convite Gravan", body),
                   text=f"Acesse {link} para ativar sua conta na Gravan e responder ao convite da editora.")
    except Exception as e:
        print(f"[agregados.cadastrar] falha enviando e-mail: {e}")

    log_event("usuario.ghost_criado", entity_type="perfil", entity_id=novo_id,
              metadata={"editora_id": g.user.id, "email": email})
    log_event("agregado.convite_enviado", entity_type="agregado_convite", entity_id=cid,
              metadata={"editora_id": g.user.id, "modo": "cadastrar", "email": email})

    return jsonify({
        "ok": True,
        "modo": "cadastrar",
        "convite_id": cid,
        "artista_id": novo_id,
        "invite_token": invite_token,
    })


# ──────────────── ADICIONAR (perfil existente) ────────────────

@agregados_bp.post("/adicionar")
@require_auth
def adicionar_agregado():
    """
    Body: { email, responsavel_aceite }

    Cria convite vinculado ao perfil existente. Notifica via sino + e-mail.
    """
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    responsavel = (data.get("responsavel_aceite") or "").strip()
    if not email or not responsavel:
        abort(400, description="E-mail e nome do responsável que aceita o termo são obrigatórios.")

    import re as _re
    resp_cpf_digits = _re.sub(r"\D", "", data.get("responsavel_cpf") or "")
    if len(resp_cpf_digits) != 11:
        abort(422, description="CPF do solicitante inválido (11 dígitos).")

    sb = get_supabase()
    editora = _ensure_publisher(sb)
    if not editora:
        abort(403, description="Apenas editoras")

    # Busca perfil completo (com PII e endereço) para preencher o termo com dados REAIS
    perfil_basico = sb.table("perfis").select("id").eq("email", email).maybe_single().execute()
    if not perfil_basico or not perfil_basico.data:
        abort(404, description='Não encontramos perfil com esse e-mail. Use "Cadastrar agregado" para criá-lo.')

    artista = _carregar_perfil_completo(sb, perfil_basico.data["id"]) or {}
    if artista.get("publisher_id") == g.user.id:
        abort(409, description="Esse artista já está agregado à sua editora.")
    if artista.get("publisher_id"):
        abort(409, description="Esse artista já está agregado a outra editora.")
    if artista.get("role") not in ("artist", "compositor", "interprete", None):
        abort(409, description="Esse perfil não é elegível para agregação.")

    # Já existe convite pendente?
    pend = sb.table("agregado_convites").select("id")\
             .eq("editora_id", g.user.id).eq("email_artista", email).eq("status", "pendente")\
             .maybe_single().execute()
    if pend and pend.data:
        abort(409, description="Já existe um convite pendente para esse e-mail.")

    termo_html = gerar_termo_html(
        editora=_editora_para_termo(editora),
        artista=_artista_para_termo(artista),
        email_artista=email,
        modo="adicionar",
    )

    convite_payload = {
        "editora_id":   g.user.id,
        "artista_id":   artista["id"],
        "email_artista": email,
        "modo":         "adicionar",
        "status":       "pendente",
        "termo_html":   termo_html,
        "termo_versao": VERSAO_ATUAL,
        "responsavel_editora_nome":     responsavel,
        "responsavel_editora_cpf_mask": _mask_cpf(resp_cpf_digits),
        "editora_aceito_ip":            _client_ip(),
    }
    res = sb.table("agregado_convites").insert(convite_payload).execute()
    cid = (res.data or [{}])[0].get("id")

    nome_editora = editora.get("razao_social") or editora.get("nome_completo") or "Editora"

    # Notificação dentro da plataforma
    notify(
        artista["id"],
        tipo="convite_editora",
        titulo=f"Convite para se agregar a {nome_editora}",
        mensagem="Toque para ler o termo e responder.",
        link="/convites",
        payload={"convite_id": cid, "editora_id": g.user.id},
    )

    # E-mail
    link = _frontend_url(f"/convites?id={cid}")
    body = f"""
      <h2 style="margin:0 0 8px">Convite de agregação editorial</h2>
      <p style="color:#444;font-size:14px">
        Olá {(artista.get('nome_artistico') or artista.get('nome_completo') or '').split(' ')[0]},
        a editora <strong>{nome_editora}</strong> está convidando você para agregar
        suas obras ao catálogo dela na Gravan.
      </p>
      <p style="color:#444;font-size:14px">
        Antes de tudo, leia atentamente o <strong>termo jurídico</strong> que define os poderes
        que você estaria concedendo. Você pode aceitar ou recusar a qualquer momento;
        nenhum vínculo se efetiva sem o seu aceite.
      </p>
      <div style="text-align:center;margin:24px 0">
        <a href="{link}" style="display:inline-block;padding:14px 28px;
           background:#BE123C;color:#fff;text-decoration:none;
           border-radius:10px;font-weight:700">Ler e responder o convite</a>
      </div>
      <p style="color:#666;font-size:12px">
        Você pode também acessar a área "Convites" na plataforma a qualquer momento.
      </p>
    """
    try:
        send_email(email, f"Convite Gravan — {nome_editora} quer te agregar",
                   _wrap_html("Convite Gravan", body),
                   text=f"A editora {nome_editora} te enviou um convite. Acesse {link} para ler e responder.")
    except Exception as e:
        print(f"[agregados.adicionar] falha enviando e-mail: {e}")

    log_event("agregado.convite_enviado", entity_type="agregado_convite", entity_id=cid,
              metadata={"editora_id": g.user.id, "modo": "adicionar", "email": email})

    return jsonify({"ok": True, "modo": "adicionar", "convite_id": cid, "artista_id": artista["id"]})


# ──────────────── CONVITES (visões editora / artista) ────────────────

@agregados_bp.get("/convites")
@require_auth
def listar_convites_enviados():
    """Convites enviados pela editora logada."""
    sb = get_supabase()
    if not _ensure_publisher(sb):
        abort(403, description="Apenas editoras")
    r = sb.table("agregado_convites").select(
        "id,email_artista,modo,status,created_at,decided_at,artista_id"
    ).eq("editora_id", g.user.id).order("created_at", desc=True).execute()
    return jsonify(r.data or [])


@agregados_bp.delete("/convites/<cid>")
@require_auth
def cancelar_convite(cid):
    """Editora cancela um convite pendente."""
    sb = get_supabase()
    if not _ensure_publisher(sb):
        abort(403, description="Apenas editoras")

    c = sb.table("agregado_convites").select("id,editora_id,status")\
          .eq("id", cid).maybe_single().execute()
    if not c or not c.data or c.data.get("editora_id") != g.user.id:
        abort(404, description="Convite não encontrado")
    if c.data.get("status") != "pendente":
        abort(409, description="Convite não está pendente")

    sb.table("agregado_convites").update({
        "status": "cancelado",
        "decided_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", cid).execute()

    log_event("agregado.convite_cancelado", entity_type="agregado_convite", entity_id=cid,
              metadata={"editora_id": g.user.id})
    return jsonify({"ok": True})


@agregados_bp.get("/convites/recebidos")
@require_auth
def listar_convites_recebidos():
    """Convites pendentes recebidos pelo artista logado (por id ou e-mail)."""
    sb = get_supabase()
    me = sb.table("perfis").select("id,email").eq("id", g.user.id).single().execute()
    if not me.data:
        abort(403)
    email = (me.data.get("email") or "").lower()

    r = sb.table("agregado_convites").select(
        "id,editora_id,modo,status,created_at,termo_versao,responsavel_editora_nome"
    ).or_(f"artista_id.eq.{g.user.id},email_artista.eq.{email}")\
     .order("created_at", desc=True).execute()

    items = r.data or []
    # Enriquecer com nome da editora
    eids = list({i["editora_id"] for i in items if i.get("editora_id")})
    nomes = {}
    if eids:
        ed = sb.table("perfis").select("id,razao_social,nome_fantasia,nome_completo")\
               .in_("id", eids).execute()
        for e in (ed.data or []):
            nomes[e["id"]] = e.get("razao_social") or e.get("nome_fantasia") or e.get("nome_completo")
    for i in items:
        i["editora_nome"] = nomes.get(i.get("editora_id"))
    return jsonify(items)


@agregados_bp.get("/convites/<cid>/termo")
@require_auth
def ver_termo(cid):
    """HTML do termo. Visível para a editora dona ou para o artista convidado."""
    sb = get_supabase()
    c = sb.table("agregado_convites").select("*").eq("id", cid).maybe_single().execute()
    if not c or not c.data:
        abort(404)
    me = sb.table("perfis").select("id,email").eq("id", g.user.id).single().execute()
    email = (me.data or {}).get("email", "").lower()
    cv = c.data
    pode_ver = (
        cv.get("editora_id") == g.user.id
        or cv.get("artista_id") == g.user.id
        or (cv.get("email_artista", "").lower() == email)
    )
    if not pode_ver:
        abort(403)
    return jsonify({
        "id":           cv["id"],
        "termo_html":   cv["termo_html"],
        "termo_versao": cv.get("termo_versao"),
        "modo":         cv.get("modo"),
        "status":       cv.get("status"),
        "editora_id":   cv.get("editora_id"),
        "responsavel_editora_nome": cv.get("responsavel_editora_nome"),
        "editora_aceito_em":        cv.get("editora_aceito_em"),
        "termo_aceito_pelo_artista_em": cv.get("termo_aceito_pelo_artista_em"),
        "assinatura_artista_nome":  cv.get("assinatura_artista_nome"),
    })


def _carregar_convite_para_decisao(sb, cid):
    """Verifica que o usuário logado é o artista do convite e que ele está pendente."""
    c = sb.table("agregado_convites").select("*").eq("id", cid).maybe_single().execute()
    if not c or not c.data:
        abort(404, description="Convite não encontrado")
    cv = c.data

    me = sb.table("perfis").select("id,email,publisher_id").eq("id", g.user.id).single().execute()
    if not me.data:
        abort(403)
    email = (me.data.get("email") or "").lower()
    if cv.get("artista_id") != g.user.id and cv.get("email_artista", "").lower() != email:
        abort(403, description="Esse convite não é seu")

    if cv.get("status") != "pendente":
        abort(409, description=f"Convite já foi {cv.get('status')}")
    return cv, me.data


@agregados_bp.post("/convites/<cid>/aceitar")
@require_auth
def aceitar_convite(cid):
    data = request.get_json(silent=True) or {}
    assinatura = (data.get("assinatura_nome") or "").strip()
    if not assinatura:
        abort(400, description="Informe seu nome completo como assinatura digital.")

    sb = get_supabase()
    cv, me = _carregar_convite_para_decisao(sb, cid)

    if me.get("publisher_id") and me["publisher_id"] != cv["editora_id"]:
        abort(409, description="Você já está agregado a outra editora. Desvincule-se primeiro.")

    agora = datetime.now(timezone.utc).isoformat()

    # Vincula
    sb.table("perfis").update({
        "publisher_id":   cv["editora_id"],
        "agregado_desde": agora,
        "is_ghost":       False,  # se era ghost, ativa de vez
    }).eq("id", g.user.id).execute()

    # Re-renderiza o termo com os dados REAIS de cadastro de ambas as partes no momento
    # do aceite, para que o documento assinado reflita exatamente o que está registrado
    # na plataforma na data do aceite (editora + artista).
    termo_final = cv.get("termo_html")
    try:
        editora_perfil = sb.table("perfis").select("*").eq("id", cv["editora_id"]).maybe_single().execute()
        artista_perfil = _carregar_perfil_completo(sb, g.user.id)
        if editora_perfil and editora_perfil.data and artista_perfil:
            termo_final = gerar_termo_html(
                editora=_editora_para_termo(editora_perfil.data),
                artista=_artista_para_termo(artista_perfil),
                email_artista=(me.get("email") or "").lower(),
                modo=cv.get("modo") or "adicionar",
            )
    except Exception as e:
        print(f"[agregados.aceitar] falha ao re-renderizar termo: {e}")

    # Marca convite
    sb.table("agregado_convites").update({
        "status":                       "aceito",
        "termo_html":                   termo_final,
        "termo_versao":                 VERSAO_ATUAL,
        "termo_aceito_pelo_artista_em": agora,
        "termo_aceito_ip":              _client_ip(),
        "assinatura_artista_nome":      assinatura,
        "artista_id":                   g.user.id,
        "decided_at":                   agora,
    }).eq("id", cid).execute()

    # Cancela quaisquer outros convites pendentes pra esse mesmo email/artista
    sb.table("agregado_convites").update({
        "status": "cancelado",
        "decided_at": agora,
    }).eq("status", "pendente").neq("id", cid).or_(
        f"artista_id.eq.{g.user.id},email_artista.eq.{(me.get('email') or '').lower()}"
    ).execute()

    # Notifica a editora
    notify(
        cv["editora_id"],
        tipo="convite_editora",
        titulo="Convite aceito",
        mensagem=f"{assinatura} aceitou seu convite e está agora agregado à sua editora.",
        link="/agregados",
        payload={"convite_id": cid, "artista_id": g.user.id},
    )

    log_event("agregado.convite_aceito", entity_type="agregado_convite", entity_id=cid,
              metadata={"editora_id": cv["editora_id"], "artista_id": g.user.id})
    return jsonify({"ok": True, "status": "aceito"})


@agregados_bp.post("/convites/<cid>/recusar")
@require_auth
def recusar_convite(cid):
    sb = get_supabase()
    cv, me = _carregar_convite_para_decisao(sb, cid)
    agora = datetime.now(timezone.utc).isoformat()
    sb.table("agregado_convites").update({
        "status":     "recusado",
        "decided_at": agora,
        "artista_id": g.user.id,
    }).eq("id", cid).execute()

    notify(
        cv["editora_id"],
        tipo="convite_editora",
        titulo="Convite recusado",
        mensagem=f"O artista {me.get('email')} recusou seu convite.",
        link="/agregados",
        payload={"convite_id": cid, "artista_id": g.user.id},
    )

    log_event("agregado.convite_recusado", entity_type="agregado_convite", entity_id=cid,
              metadata={"editora_id": cv["editora_id"], "artista_id": g.user.id})
    return jsonify({"ok": True, "status": "recusado"})


# ──────────────── BACKWARD-COMPAT: POST raiz ────────────────

@agregados_bp.post("")
@require_auth
def criar_legacy():
    """Compat: redireciona para /cadastrar (mesma semântica antiga)."""
    return cadastrar_agregado()


# ──────────────── CONSULTAS (editora) ────────────────

@agregados_bp.get("/<aid>")
@require_auth
def detalhes(aid):
    sb = get_supabase()
    if not _ensure_publisher(sb):
        abort(403, description="Apenas editoras")

    r = sb.table("perfis").select("*").eq("id", aid).eq("publisher_id", g.user.id).maybe_single().execute()
    if not r or not r.data:
        abort(404, description="Agregado não encontrado")
    return jsonify(r.data)


@agregados_bp.delete("/<aid>")
@require_auth
def desvincular(aid):
    sb = get_supabase()
    if not _ensure_publisher(sb):
        abort(403, description="Apenas editoras")

    r = sb.table("perfis").select("id,publisher_id").eq("id", aid).maybe_single().execute()
    if not r or not r.data or r.data.get("publisher_id") != g.user.id:
        abort(404, description="Agregado não encontrado")

    sb.table("perfis").update({"publisher_id": None, "agregado_desde": None}).eq("id", aid).execute()
    log_event("agregado.removido", entity_type="perfil", entity_id=aid,
              metadata={"editora_id": g.user.id})
    return jsonify({"ok": True})


@agregados_bp.get("/<aid>/dashboard")
@require_auth
def dashboard_agregado(aid):
    """Dashboard do agregado, visto pela editora."""
    sb = get_supabase()
    if not _ensure_publisher(sb):
        abort(403, description="Apenas editoras")

    perfil = sb.table("perfis").select("id,nome_completo,nome_artistico,publisher_id").eq("id", aid).maybe_single().execute()
    if not perfil or not perfil.data or perfil.data.get("publisher_id") != g.user.id:
        abort(403, description="Agregado não pertence a esta editora")

    obras_autoria = sb.table("obras_autores").select("obra_id").eq("perfil_id", aid).execute()
    obras_ids = list({o["obra_id"] for o in (obras_autoria.data or [])})

    obras = []
    if obras_ids:
        obras = sb.table("obras").select("id,titulo,publicada,created_at").in_("id", obras_ids).execute().data or []

    contratos = sb.table("contracts_edicao").select("*").eq("autor_id", aid).execute()

    ganhos_total = 0
    ganhos_retidos = 0
    try:
        repasses = sb.table("repasses").select("valor_cents,status").eq("perfil_id", aid).execute()
        ganhos_total = sum(r.get("valor_cents", 0) for r in (repasses.data or []) if r["status"] == "enviado")
        ganhos_retidos = sum(r.get("valor_cents", 0) for r in (repasses.data or []) if r["status"] == "retido")
    except Exception:
        pass

    return jsonify({
        "perfil":           perfil.data,
        "total_obras":      len(obras),
        "obras":            obras,
        "contratos":        contratos.data or [],
        "ganhos_cents":     ganhos_total,
        "ganhos_retidos_cents": ganhos_retidos,
    })


@agregados_bp.get("/minha-editora")
@require_auth
def minha_editora():
    """Retorna a editora à qual o artista autenticado está agregado, se houver."""
    sb = get_supabase()
    meu = sb.table("perfis").select("id,publisher_id").eq("id", g.user.id).single().execute()
    if not meu.data:
        abort(404)
    pid = meu.data.get("publisher_id")
    if not pid:
        return jsonify(None)
    editora = sb.table("perfis").select(
        "id,nome,nome_fantasia,razao_social,email,telefone"
    ).eq("id", pid).maybe_single().execute()
    if not editora.data:
        return jsonify(None)
    d = editora.data
    return jsonify({
        "id":    d.get("id"),
        "nome":  d.get("razao_social") or d.get("nome_fantasia") or d.get("nome") or "",
        "email": d.get("email") or "",
        "telefone": d.get("telefone") or "",
    })
