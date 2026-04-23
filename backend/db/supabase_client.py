"""
Cliente Supabase com service_role key.
Usado apenas no backend — nunca expor ao frontend.
"""
import os
from supabase import create_client, Client

_client: Client | None = None


def get_supabase() -> Client:
    global _client
    if _client is None:
        url = os.environ["SUPABASE_URL"]
        key = os.environ["SUPABASE_SERVICE_KEY"]  # service_role — acesso total
        _client = create_client(url, key)
    return _client


def get_supabase_for_user(jwt: str) -> Client:
    """
    Cria um cliente autenticado com o JWT do usuário.
    As políticas RLS são aplicadas automaticamente.
    """
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_KEY"]
    client = create_client(url, key)
    client.auth.set_session(jwt, "")
    return client
