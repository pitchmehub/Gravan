"""
Routes: /api/ai
Endpoints para funcionalidades de IA (gratuitas):
  • POST /api/ai/transcrever            → Whisper local (faster-whisper)
  • POST /api/ai/obras/<id>/gerar-capa  → Pollinations.ai (regerar capa)
  • POST /api/ai/obras/<id>/transcrever → re-transcreve áudio existente
"""
import logging
import secrets
from flask import Blueprint, request, jsonify, g, abort
from middleware.auth import require_auth
from db.supabase_client import get_supabase
from services.ai_letra import transcrever_audio_bytes, transcrever_obra_async
from services.ai_capa import gerar_e_salvar_capa, gerar_url_capa
from app import limiter

log = logging.getLogger(__name__)
ai_bp = Blueprint("ai", __name__)

MAX_AUDIO_BYTES = 10 * 1024 * 1024  # 10 MB


@ai_bp.route("/transcrever", methods=["POST"])
@require_auth
@limiter.limit("5 per hour")
def transcrever_audio_upload():
    """
    Transcreve um arquivo .mp3 enviado pelo usuário (sem persistir).
    Usado no formulário de Nova Obra antes do cadastro.
    Bloqueante: pode levar 30s a 2min dependendo do tamanho do áudio.
    """
    if "audio" not in request.files:
        abort(422, description="Campo 'audio' é obrigatório.")
    audio_file = request.files["audio"]
    if not audio_file.filename.lower().endswith(".mp3"):
        abort(422, description="Apenas arquivos .mp3 são aceitos.")

    audio_bytes = audio_file.read()
    if len(audio_bytes) > MAX_AUDIO_BYTES:
        abort(413, description="Arquivo excede 10 MB.")
    if not audio_bytes:
        abort(422, description="Arquivo de áudio vazio.")

    try:
        letra = transcrever_audio_bytes(audio_bytes, language="pt")
    except Exception as e:
        log.exception("[ai] falha na transcrição: %s", e)
        abort(500, description="Falha ao transcrever o áudio. Tente novamente.")

    return jsonify({
        "letra": letra,
        "chars": len(letra),
    }), 200


@ai_bp.route("/obras/<obra_id>/gerar-capa", methods=["POST"])
@require_auth
@limiter.limit("10 per hour")
def gerar_capa_obra(obra_id):
    """Gera (ou regera) a capa da obra via Pollinations.ai."""
    sb = get_supabase()
    obra = sb.table("obras").select("id, nome, genero, titular_id").eq("id", obra_id).single().execute()
    if not obra.data:
        abort(404, description="Obra não encontrada.")

    perfil = sb.table("perfis").select("role").eq("id", g.user.id).single().execute()
    is_admin = perfil.data and perfil.data.get("role") == "administrador"
    if obra.data["titular_id"] != g.user.id and not is_admin:
        abort(403, description="Apenas o titular pode gerar a capa desta obra.")

    # Seed aleatória para que cada chamada gere uma capa diferente
    seed = secrets.randbelow(10_000_000)
    url = gerar_e_salvar_capa(
        obra_id=obra.data["id"],
        nome=obra.data["nome"],
        genero=obra.data.get("genero") or "OUTROS",
        seed=seed,
    )
    if not url:
        abort(500, description="Falha ao gerar a capa.")

    return jsonify({"cover_url": url}), 200


@ai_bp.route("/obras/<obra_id>/transcrever", methods=["POST"])
@require_auth
@limiter.limit("5 per hour")
def retranscrever_obra(obra_id):
    """
    Re-transcreve o áudio de uma obra já cadastrada.
    Baixa o áudio do Storage e dispara transcrição em background.
    """
    sb = get_supabase()
    obra = sb.table("obras").select("id, titular_id, audio_path").eq("id", obra_id).single().execute()
    if not obra.data:
        abort(404, description="Obra não encontrada.")

    perfil = sb.table("perfis").select("role").eq("id", g.user.id).single().execute()
    is_admin = perfil.data and perfil.data.get("role") == "administrador"
    if obra.data["titular_id"] != g.user.id and not is_admin:
        abort(403, description="Apenas o titular pode re-transcrever esta obra.")

    audio_path = obra.data.get("audio_path")
    if not audio_path:
        abort(404, description="Áudio da obra não encontrado.")

    try:
        audio_bytes = sb.storage.from_("obras-audio").download(audio_path)
    except Exception as e:
        log.exception("[ai] falha ao baixar áudio: %s", e)
        abort(500, description="Falha ao baixar áudio da obra.")

    transcrever_obra_async(obra_id=obra_id, audio_bytes=audio_bytes, language="pt")
    return jsonify({"ok": True, "letra_status": "transcrevendo"}), 202
