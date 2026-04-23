"""
Route do projeto — REMOVIDA por motivo de segurança.

A versão original servia o ZIP do código-fonte (`/app/pitch_me_projeto_completo.zip`)
publicamente, sem autenticação. Isso vazaria o source code completo da aplicação
para qualquer atacante que descobrisse a URL `/api/download-projeto`.

Mantemos o blueprint vazio para não quebrar o registro em app.py.
Caso precise de download interno, exija @require_auth + role administrador.
"""
from flask import Blueprint

download_bp = Blueprint("download", __name__)
