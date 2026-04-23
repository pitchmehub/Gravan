"""Route: /api/contato - endpoint publico para mensagens da landing."""
import re
from flask import Blueprint, request, jsonify, abort
from db.supabase_client import get_supabase
from utils.sanitizer import sanitize_text
from utils.crypto import hash_ip
from app import limiter

contato_bp = Blueprint("contato", __name__)
EMAIL_RE = re.compile(r"^[^@]+@[^@]+\.[^@]+$")


@contato_bp.route("/", methods=["POST"])
@limiter.limit("3 per hour")
def enviar_mensagem():
    data = request.get_json(force=True, silent=True) or {}

    nome = (data.get("nome") or "").strip()
    email = (data.get("email") or "").strip().lower()
    mensagem_raw = (data.get("mensagem") or "").strip()

    if not nome or len(nome) < 2 or len(nome) > 120:
        abort(422, description="Nome invalido (entre 2 e 120 caracteres).")
    if not email or not EMAIL_RE.match(email) or len(email) > 200:
        abort(422, description="Email invalido.")
    if not mensagem_raw:
        abort(422, description="Mensagem e obrigatoria.")

    try:
        mensagem = sanitize_text(mensagem_raw, max_length=1000)
    except ValueError as e:
        abort(422, description=str(e))

    if len(mensagem) < 10:
        abort(422, description="A mensagem precisa ter pelo menos 10 caracteres.")

    sb = get_supabase()
    try:
        sb.table("contato_mensagens").insert({
            "nome":      sanitize_text(nome, max_length=120),
            "email":     email,
            "mensagem":  mensagem,
            "ip_origem": hash_ip(request.remote_addr or ""),
        }).execute()
    except Exception as e:
        abort(500, description=f"Erro ao salvar mensagem: {str(e)}")

    return jsonify({"ok": True}), 201