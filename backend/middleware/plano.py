"""
Middleware/decorator @require_pro — bloqueia rotas apenas para assinantes PRO.

Uso:
    from middleware.plano import require_pro

    @some_bp.route("/analytics")
    @require_auth
    @require_pro
    def analytics(): ...

Deve vir DEPOIS de @require_auth (depende de g.user).
"""
from functools import wraps
from flask import abort, g
from db.supabase_client import get_supabase


def require_pro(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not getattr(g, "user", None):
            abort(401, description="Autenticação obrigatória.")
        sb = get_supabase()
        try:
            r = sb.table("perfis").select("plano, status_assinatura").eq("id", g.user.id).single().execute()
            p = r.data or {}
        except Exception:
            # Coluna ainda não existe — trata como STARTER
            p = {}
        plano = p.get("plano", "STARTER")
        status = p.get("status_assinatura", "inativa")
        # PRO efetivo: plano PRO e assinatura em dia (ativa, cancelada-mas-não-expirada, past_due)
        if plano != "PRO" or status not in ("ativa", "cancelada", "past_due"):
            abort(402, description="Recurso exclusivo para assinantes PRO. Atualize seu plano em /planos.")
        return fn(*args, **kwargs)
    return wrapper
