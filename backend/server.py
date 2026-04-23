"""
Pitch.me — Entry point for both ASGI and WSGI.
"""
import os
import sys

# Adiciona o diretório atual ao path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from app import create_app
from asgiref.wsgi import WsgiToAsgi

# Cria a aplicação Flask
flask_app = create_app()

# Para uvicorn (ASGI)
app = WsgiToAsgi(flask_app)

# Para execução direta
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8001))
    flask_app.run(
        debug=False,
        host="0.0.0.0",
        port=port,
        threaded=True
    )
