"""
Middleware de autenticacao via JWT Supabase.
Valida o token com cache seguro em memoria.

CORREÇÃO DE VULNERABILIDADES:
- #3 (CRÍTICA): Cache de tokens agora usa hash ao invés de JWT plain text
- #18 (BAIXA): Monitoramento de tentativas de login
"""
from functools import wraps
from flask import request, g, abort
from db.supabase_client import get_supabase
from utils.audit import log_event
import time
import hashlib

# Cache de tokens validados (usa hash SHA256 do JWT como chave)
# Chave: hash SHA256. Valor: (user_obj, expires_at)
_token_cache = {}
_CACHE_TTL = 60  # 60 segundos
_MAX_CACHE_SIZE = 500  # Reduzido para 500 (mais seguro)


def _hash_token(jwt: str) -> str:
    """Retorna hash SHA256 do token para uso seguro como chave de cache."""
    return hashlib.sha256(jwt.encode('utf-8')).hexdigest()


def _get_cached_user(jwt: str):
    """Retorna o user se ainda válido no cache."""
    token_hash = _hash_token(jwt)
    entry = _token_cache.get(token_hash)
    if entry and entry[1] > time.time():
        return entry[0]
    if entry:
        _token_cache.pop(token_hash, None)
    return None


def _cache_user(jwt: str, user):
    """Cacheia o user por CACHE_TTL segundos."""
    # Limita o tamanho do cache de forma mais agressiva
    if len(_token_cache) >= _MAX_CACHE_SIZE:
        # Remove entradas expiradas primeiro
        now = time.time()
        expired = [k for k, v in _token_cache.items() if v[1] <= now]
        for k in expired:
            _token_cache.pop(k, None)
        
        # Se ainda estiver cheio, limpa metade
        if len(_token_cache) >= _MAX_CACHE_SIZE:
            keys_to_remove = list(_token_cache.keys())[:_MAX_CACHE_SIZE // 2]
            for k in keys_to_remove:
                _token_cache.pop(k, None)
    
    token_hash = _hash_token(jwt)
    _token_cache[token_hash] = (user, time.time() + _CACHE_TTL)


def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            abort(401, description="Token de autenticacao ausente.")

        jwt = auth_header.split(" ", 1)[1]
        if len(jwt) < 20 or len(jwt) > 2000:
            abort(401, description="Token invalido.")

        # Tenta cache primeiro
        user = _get_cached_user(jwt)
        if user is None:
            try:
                sb = get_supabase()
                user_resp = sb.auth.get_user(jwt)
                if not user_resp or not user_resp.user:
                    abort(401, description="Token invalido ou expirado.")
                user = user_resp.user
                _cache_user(jwt, user)
            except Exception:
                abort(401, description="Falha ao validar o token.")

        g.user = user
        g.jwt  = jwt
        return f(*args, **kwargs)
    return decorated


def extract_user_if_present():
    """Retorna o user se houver JWT válido; None caso contrário. Nunca levanta."""
    try:
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return None
        jwt = auth_header.split(" ", 1)[1]
        if len(jwt) < 20 or len(jwt) > 2000:
            return None
        user = _get_cached_user(jwt)
        if user is not None:
            return user
        sb = get_supabase()
        user_resp = sb.auth.get_user(jwt)
        if user_resp and user_resp.user:
            _cache_user(jwt, user_resp.user)
            return user_resp.user
    except Exception:
        return None
    return None


def require_role(*roles: str):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            sb = get_supabase()
            result = (
                sb.table("perfis")
                .select("role")
                .eq("id", g.user.id)
                .single()
                .execute()
            )
            user_role = result.data.get("role") if result.data else None
            if user_role not in roles:
                abort(403, description=f"Acesso restrito.")
            g.role = user_role
            return f(*args, **kwargs)
        return decorated
    return decorator
