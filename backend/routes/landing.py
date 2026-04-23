"""Routes: /api/landing — leitura pública + edição admin.

CORREÇÃO PENTEST: A versão antiga gravava em `config/landing.json` no
disco local. No Render free (e em qualquer container) o disco é efêmero,
então cada deploy ou restart *apagava* todas as edições do administrador.
Agora gravamos em uma única linha JSON na tabela `landing_content`
(id = '__landing_full__').
"""
import json
from flask import Blueprint, jsonify, request, abort, g
from middleware.auth import require_auth
from db.supabase_client import get_supabase

landing_bp = Blueprint("landing", __name__)

FULL_LANDING_KEY = "__landing_full__"


def _read_config(sb):
    """Lê o JSON consolidado da landing salvo no Supabase."""
    try:
        r = sb.table("landing_content").select("valor").eq("id", FULL_LANDING_KEY).maybe_single().execute()
        valor = ((r.data if r else None) or {}).get("valor") or "{}"
        return json.loads(valor) if isinstance(valor, str) else (valor or {})
    except Exception:
        return {}


def _write_config(sb, payload: dict):
    sb.table("landing_content").upsert({
        "id":    FULL_LANDING_KEY,
        "valor": json.dumps(payload, ensure_ascii=False),
    }).execute()


@landing_bp.route("/content", methods=["GET"])
def get_landing_content():
    """Público — devolve a configuração atual da landing."""
    sb = get_supabase()
    cfg = _read_config(sb)
    # Templates de contrato (chaves dedicadas no Supabase)
    try:
        r = sb.table("landing_content").select("id, valor").in_(
            "id", ["contrato_licenciamento_template", "contrato_edicao_template"]
        ).execute()
        for row in (r.data or []):
            cfg[row["id"]] = row.get("valor", "")
    except Exception:
        pass
    return jsonify(cfg), 200


@landing_bp.route("/content", methods=["PUT"])
@require_auth
def update_landing_content():
    """Admin-only — salva nova configuração no Supabase."""
    sb = get_supabase()
    try:
        r = sb.table("perfis").select("role").eq("id", g.user.id).maybe_single().execute()
        role = ((r.data if r else None) or {}).get("role")
    except Exception:
        role = None
    if role != "administrador":
        abort(403, description="Acesso restrito a administradores.")

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or not payload:
        abort(400, description="Payload inválido: envie o JSON completo da landing.")

    try:
        _write_config(sb, payload)
    except Exception as e:
        abort(500, description=f"Erro ao salvar landing: {str(e)[:200]}")

    return jsonify({"ok": True, "saved_keys": list(payload.keys())}), 200
