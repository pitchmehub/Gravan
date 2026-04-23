"""
Handlers globais de erro — respostas JSON padronizadas.

CORREÇÃO DE VULNERABILIDADE #7 (ALTA): Logs de erro seguros.
Não expõe stack traces ou informações sensíveis ao cliente.
"""
import logging
from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException

# Configure structured logging (não expõe detalhes ao cliente)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger('pitchme')


def register_error_handlers(app: Flask) -> None:

    @app.errorhandler(400)
    def bad_request(e):
        return jsonify({"error": str(e.description)}), 400

    @app.errorhandler(401)
    def unauthorized(e):
        return jsonify({"error": str(e.description)}), 401

    @app.errorhandler(403)
    def forbidden(e):
        return jsonify({"error": str(e.description)}), 403

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": str(e.description)}), 404

    @app.errorhandler(409)
    def conflict(e):
        return jsonify({"error": str(e.description)}), 409

    @app.errorhandler(413)
    def request_entity_too_large(e):
        return jsonify({"error": "Arquivo excede o limite de 10 MB."}), 413

    @app.errorhandler(422)
    def unprocessable(e):
        return jsonify({"error": str(e.description)}), 422

    @app.errorhandler(500)
    def internal(e):
        # Log interno detalhado (não enviado ao cliente)
        logger.error(f"Internal error: {str(e)}", exc_info=True)
        # Se foi abort(500, description="..."), expõe a description (é intencional)
        if isinstance(e, HTTPException) and e.description and \
                e.description != "Internal Server Error":
            return jsonify({"error": str(e.description)}), 500
        # Caso contrário (exceção não tratada), resposta genérica
        return jsonify({"error": "Erro interno do servidor. Nossa equipe foi notificada."}), 500
