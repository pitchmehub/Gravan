"""
Entrypoint para a publicação (deploy) do app no Replit.

O gunicorn de produção carrega `main:app`. Aqui apenas adicionamos a pasta
`backend/` ao caminho de importação e re-exportamos o `app` Flask, que já
serve a API em `/api/...` e (quando há um build do frontend em
`frontend/dist`) também serve o React como SPA. Em desenvolvimento, este
arquivo não é usado — o Vite serve o frontend em outra porta.
"""
import os
import sys

_HERE    = os.path.dirname(os.path.abspath(__file__))
_BACKEND = os.path.join(_HERE, "backend")
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from app import app  # noqa: E402,F401


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
