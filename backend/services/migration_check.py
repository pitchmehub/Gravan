"""Helpers para detectar se a migração de assinatura já foi aplicada no DB."""
import time
from db.supabase_client import get_supabase

# Cache:
#   - Positivo (True) é permanente — migração não desaparece
#   - Negativo (False) expira em 30s — permite detectar migração recém-aplicada
#     sem precisar reiniciar o backend.
_cache = {"ok": False, "checked_at": 0.0, "is_positive": False}
_NEGATIVE_TTL = 30  # segundos


def migration_applied() -> bool:
    # Cache positivo permanente
    if _cache["is_positive"]:
        return True
    # Cache negativo com TTL
    if _cache["checked_at"] and (time.time() - _cache["checked_at"] < _NEGATIVE_TTL):
        return _cache["ok"]

    try:
        sb = get_supabase()
        sb.table("perfis").select("plano,status_assinatura").limit(1).execute()
        sb.table("favoritos").select("id").limit(1).execute()
        _cache["ok"] = True
        _cache["is_positive"] = True
    except Exception:
        _cache["ok"] = False
        _cache["is_positive"] = False
    _cache["checked_at"] = time.time()
    return _cache["ok"]


def reset_cache():
    _cache["ok"] = False
    _cache["is_positive"] = False
    _cache["checked_at"] = 0.0
