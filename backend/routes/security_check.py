"""Routes: /api/admin/security-check — diagnóstico de segurança visível apenas ao admin."""
from flask import Blueprint, jsonify, g, abort
from middleware.auth import require_auth
from db.supabase_client import get_supabase
import os, requests, time

security_bp = Blueprint("security_check", __name__)


def _is_admin() -> bool:
    try:
        r = get_supabase().table("perfis").select("role").eq("id", g.user.id).maybe_single().execute()
        return ((r.data if r else None) or {}).get("role") == "administrador"
    except Exception:
        return False


@security_bp.route("/security-check", methods=["GET"])
@require_auth
def security_check():
    if not _is_admin():
        abort(403, description="Acesso restrito a administradores.")

    url  = os.environ["SUPABASE_URL"]
    anon = os.environ.get("SUPABASE_ANON_KEY") or ""

    # Lista de tabelas a checar
    tables = ["perfis", "obras", "wallets", "transacoes", "saques", "ofertas", "contato_mensagens"]
    results = []

    for t in tables:
        if not anon:
            results.append({"table": t, "status": "unknown", "message": "SUPABASE_ANON_KEY não configurada no backend"})
            continue
        try:
            r = requests.get(
                f"{url}/rest/v1/{t}?select=*&limit=1",
                headers={"apikey": anon, "Authorization": f"Bearer {anon}"},
                timeout=5,
            )
            if r.status_code == 200:
                rows = r.json() if isinstance(r.json(), list) else []
                if len(rows) > 0:
                    results.append({"table": t, "status": "leak", "message": f"⚠️ Exposto a anon — {len(rows)} row(s) vazaram"})
                else:
                    results.append({"table": t, "status": "ok-empty", "message": "RLS ativo ou tabela vazia (0 rows via anon)"})
            elif r.status_code in (401, 403):
                results.append({"table": t, "status": "ok-blocked", "message": f"✓ Bloqueado (HTTP {r.status_code})"})
            elif r.status_code == 404:
                results.append({"table": t, "status": "n/a", "message": "Tabela não existe"})
            else:
                results.append({"table": t, "status": "error", "message": f"HTTP {r.status_code}"})
        except Exception as e:
            results.append({"table": t, "status": "error", "message": str(e)[:100]})

    return jsonify({
        "checked_at": int(time.time()),
        "env": os.getenv("FLASK_ENV", "development"),
        "allowed_origins": [o.strip() for o in (os.getenv("ALLOWED_ORIGINS") or "").split(",") if o.strip()],
        "tables": results,
    }), 200
