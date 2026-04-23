"""
WSGI entry point for Gunicorn.
"""
import os
import sys

# Garante que o diretório atual está no path
sys.path.insert(0, os.path.dirname(__file__))

# Importa a aplicação
from app import create_app

application = create_app()
app = application  # Alias para compatibilidade

if __name__ == "__main__":
    application.run(host="0.0.0.0", port=8001, debug=False)