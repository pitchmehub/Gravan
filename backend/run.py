"""
Entrypoint do servidor Gravan.
Uso local:  python run.py
Produção:   gunicorn "run:app" --workers 4 --bind 0.0.0.0:8000
"""
from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False)
