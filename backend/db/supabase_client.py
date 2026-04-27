"""
Cliente Supabase com service_role key.
Usado apenas no backend — nunca expor ao frontend.
"""
import os
import re
from supabase import create_client, Client

_client: Client | None = None


def _clean_url(raw: str) -> str:
    """Sanitiza a URL caso o secret tenha sido salvo com formatação
    markdown do tipo `[https://x.supabase.co](https://x.supabase.co)`,
    ou com aspas/espaços extras. Sem isso, qualquer wrapping desse tipo
    quebra TODAS as chamadas ao Supabase com 'Invalid URL'."""
    if not raw:
        return raw
    s = raw.strip().strip('"').strip("'")
    # markdown link: [texto](url)  →  pega o conteúdo dos parênteses
    m = re.match(r"^\[[^\]]+\]\((https?://[^)\s]+)\)\s*$", s)
    if m:
        return m.group(1)
    # link envolto apenas em colchetes: [https://...]
    if s.startswith("[") and s.endswith("]"):
        inner = s[1:-1].strip()
        if inner.startswith(("http://", "https://")):
            return inner
    return s


def _service_key() -> str:
    return (
        os.environ.get("SUPABASE_SERVICE_KEY")
        or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        or os.environ["SUPABASE_SERVICE_KEY"]
    ).strip().strip('"').strip("'")


def get_supabase() -> Client:
    global _client
    if _client is None:
        url = _clean_url(os.environ["SUPABASE_URL"])
        key = _service_key()  # service_role — acesso total
        _client = create_client(url, key)
    return _client


def get_supabase_for_user(jwt: str) -> Client:
    """
    Cria um cliente autenticado com o JWT do usuário.
    As políticas RLS são aplicadas automaticamente.
    """
    url = _clean_url(os.environ["SUPABASE_URL"])
    key = _service_key()
    client = create_client(url, key)
    client.auth.set_session(jwt, "")
    return client
