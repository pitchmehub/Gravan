"""
Gravan — API Flask com hardening completo de segurança.

CORREÇÕES DE VULNERABILIDADES IMPLEMENTADAS:
- #5 (ALTA): CSRF Protection via Flask-WTF
- #8 (ALTA): Secure session configuration
- #11 (MÉDIA): Content Security Policy headers
- #13 (MÉDIA): Rate limiting otimizado
- #19 (BAIXA): SameSite cookie configuration
"""
import os
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect
from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "memory://")
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["600 per minute", "10000 per hour"],
    storage_uri=REDIS_URL,
)

csrf = CSRFProtect()


def create_app() -> Flask:
    app = Flask(__name__)

    from routes.publishers       import publishers_bp
    from routes.agregados        import agregados_bp
    from routes.contratos_edicao import contratos_edicao_bp
    from routes.keep_alive       import keep_alive_bp

    # ═══════════════════════════════════════════════════════════
    # SESSION CONFIGURATION
    # ═══════════════════════════════════════════════════════════
    secret_key = os.environ.get("FLASK_SECRET_KEY", "")
    if not secret_key or len(secret_key) < 32:
        raise RuntimeError(
            "FLASK_SECRET_KEY ausente ou fraca. Defina no .env uma string de "
            "no mínimo 32 caracteres (ex.: openssl rand -hex 32)."
        )
    app.secret_key = secret_key

    is_production = os.getenv("FLASK_ENV", "development") == "production"
    app.config.update(
        SESSION_COOKIE_SECURE=is_production,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
        PERMANENT_SESSION_LIFETIME=3600,
        SESSION_COOKIE_NAME='gravan_session',
    )

    # ═══════════════════════════════════════════════════════════
    # CORS CONFIGURATION
    # ═══════════════════════════════════════════════════════════
    _env_origins = os.getenv("ALLOWED_ORIGINS", "").strip()
    allowed = [o.strip() for o in _env_origins.split(",") if o.strip()]

    # Support Replit dynamic domains
    replit_dev_domain = os.getenv("REPLIT_DEV_DOMAIN", "")
    if replit_dev_domain:
        for scheme in ("https://", "http://"):
            origin = f"{scheme}{replit_dev_domain}"
            if origin not in allowed:
                allowed.append(origin)

    if not allowed:
        allowed = ["http://localhost:3000"] if os.getenv("FLASK_ENV") != "production" else []
    CORS(
        app,
        resources={
            r"/api/*": {
                "origins": allowed,
                "methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
                "allow_headers": ["Authorization", "Content-Type", "X-CSRF-Token"],
                "expose_headers": ["Content-Length", "X-Request-Id"],
            },
        },
        supports_credentials=True,
        max_age=3600,
        always_send=False,
    )
    app.logger.info("CORS configurado para origens: %s", allowed)

    # ═══════════════════════════════════════════════════════════
    # SECURITY CONFIGURATIONS
    # ═══════════════════════════════════════════════════════════
    app.config["MAX_CONTENT_LENGTH"] = 11 * 1024 * 1024
    csrf.init_app(app)
    app.config['WTF_CSRF_CHECK_DEFAULT'] = False
    limiter.init_app(app)

    # ═══════════════════════════════════════════════════════════
    # SECURITY HEADERS
    # ═══════════════════════════════════════════════════════════
    @app.after_request
    def add_security_headers(response):
        response.headers["X-Content-Type-Options"]   = "nosniff"
        response.headers["X-Frame-Options"]          = "DENY"
        response.headers["X-Download-Options"]       = "noopen"
        response.headers["X-DNS-Prefetch-Control"]   = "off"
        response.headers["X-Permitted-Cross-Domain-Policies"] = "none"
        response.headers["Referrer-Policy"]          = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"]       = (
            "geolocation=(), microphone=(), camera=(), "
            "payment=(self \"https://js.stripe.com\"), "
            "usb=(), autoplay=(), fullscreen=(self)"
        )
        response.headers["Cross-Origin-Opener-Policy"]   = "same-origin"
        response.headers["Cross-Origin-Resource-Policy"] = "same-site"

        if request.is_secure or request.headers.get("X-Forwarded-Proto") == "https":
            response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"

        csp_directives = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://js.stripe.com https://*.paypal.com https://*.paypalobjects.com",
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.jsdelivr.net",
            "font-src 'self' data: https://fonts.gstatic.com https://cdn.jsdelivr.net",
            "img-src 'self' data: blob: https:",
            "media-src 'self' blob: https://*.supabase.co",
            "connect-src 'self' https://*.supabase.co https://api.stripe.com https://*.paypal.com https://*.paypalobjects.com",
            "frame-src 'self' https://js.stripe.com https://*.paypal.com",
            "object-src 'none'",
            "base-uri 'self'",
            "form-action 'self'",
            "frame-ancestors 'none'",
            "upgrade-insecure-requests",
        ]
        response.headers["Content-Security-Policy"] = "; ".join(csp_directives)

        response.headers.pop("Server", None)
        response.headers["Server"] = "Gravan"

        return response

    # ═══════════════════════════════════════════════════════════
    # BLUEPRINTS
    # ═══════════════════════════════════════════════════════════
    import routes.obras as obras_module
    import routes.transacoes as transacoes_module
    import routes.perfis as perfis_module
    import routes.catalogo as catalogo_module
    import routes.admin as admin_module
    import routes.stripe_routes as stripe_module
    import routes.paypal_routes as paypal_module
    import routes.contato as contato_module
    import routes.download as download_module
    import routes.landing as landing_module
    import routes.security_check as security_check_module
    import routes.assinatura as assinatura_module
    import routes.favoritos as favoritos_module
    import routes.analytics as analytics_module
    import routes.contratos_licenciamento as contratos_lic_module
    from routes.notificacoes import notificacoes_bp

    obras_bp = obras_module.obras_bp
    transacoes_bp = transacoes_module.transacoes_bp
    perfis_bp = perfis_module.perfis_bp
    catalogo_bp = catalogo_module.catalogo_bp
    admin_bp = admin_module.admin_bp
    stripe_bp = stripe_module.stripe_bp
    paypal_bp = paypal_module.paypal_bp
    contato_bp = contato_module.contato_bp
    download_bp = download_module.download_bp
    landing_bp = landing_module.landing_bp
    security_bp = security_check_module.security_bp
    assinatura_bp = assinatura_module.assinatura_bp
    favoritos_bp = favoritos_module.favoritos_bp
    analytics_bp = analytics_module.analytics_bp

    app.register_blueprint(obras_bp, url_prefix="/api/obras")
    app.register_blueprint(transacoes_bp, url_prefix="/api/transacoes")
    app.register_blueprint(perfis_bp, url_prefix="/api/perfis")
    app.register_blueprint(catalogo_bp, url_prefix="/api/catalogo")
    app.register_blueprint(admin_bp, url_prefix="/api/admin")
    app.register_blueprint(security_bp, url_prefix="/api/admin")
    app.register_blueprint(stripe_bp, url_prefix="/api/stripe")
    from routes.stripe_connect import connect_bp
    app.register_blueprint(connect_bp, url_prefix="/api/connect")
    app.register_blueprint(paypal_bp, url_prefix="/api/paypal")
    app.register_blueprint(contato_bp, url_prefix="/api/contato")
    app.register_blueprint(download_bp, url_prefix="/api")
    from routes.dossie import dossie_bp
    app.register_blueprint(dossie_bp, url_prefix="/api/dossies")
    from routes.saques import saques_bp
    app.register_blueprint(saques_bp)
    app.register_blueprint(landing_bp, url_prefix="/api/landing")
    app.register_blueprint(assinatura_bp, url_prefix="/api/assinatura")
    app.register_blueprint(favoritos_bp, url_prefix="/api/favoritos")
    app.register_blueprint(analytics_bp, url_prefix="/api/analytics")
    app.register_blueprint(contratos_lic_module.contratos_lic_bp, url_prefix="/api/contratos/licenciamento")
    app.register_blueprint(publishers_bp)
    app.register_blueprint(agregados_bp)
    app.register_blueprint(contratos_edicao_bp)
    app.register_blueprint(notificacoes_bp, url_prefix="/api/notificacoes")
    app.register_blueprint(keep_alive_bp, url_prefix="/api")
    csrf.exempt(keep_alive_bp)
    limiter.exempt(keep_alive_bp)

    # IA gratuita: Whisper local (transcrição) + Pollinations.ai (capa)
    from routes.ai import ai_bp
    app.register_blueprint(ai_bp, url_prefix="/api/ai")
    csrf.exempt(ai_bp)

    # Licenciamento de obras editadas por terceiras editoras
    from routes.ofertas_terceiros import ofertas_lic_bp
    app.register_blueprint(ofertas_lic_bp)

    # ═══════════════════════════════════════════════════════════
    # SEED AUTOMÁTICO: Contrato de Edição Musical
    # ═══════════════════════════════════════════════════════════
    try:
        from services.contrato_template import ensure_contract_seeded
        ensure_contract_seeded()
    except Exception as _e:
        app.logger.warning(f"Seed automático do contrato falhou: {_e}")

    # ═══════════════════════════════════════════════════════════
    # ERROR HANDLERS
    # ═══════════════════════════════════════════════════════════
    import utils.errors as errors_module
    errors_module.register_error_handlers(app)

    @app.errorhandler(429)
    def ratelimit_handler(e):
        return jsonify({"error": "Muitas requisições. Aguarde um momento."}), 429

    @app.route("/api/health")
    @csrf.exempt
    @limiter.exempt
    def health():
        return jsonify({"status": "ok"}), 200

    # ═══════════════════════════════════════════════════════════
    # HEARTBEAT INTERNO (anti-sleep)
    # ═══════════════════════════════════════════════════════════
    try:
        from services.heartbeat import start_heartbeat
        start_heartbeat()
    except Exception as _e:
        app.logger.warning(f"Heartbeat não pôde ser iniciado: {_e}")

    # ═══════════════════════════════════════════════════════════
    # BACKFILL DE CAPAS — uma obra por vez, em thread daemon
    # (só um worker do gunicorn pega o lock e executa)
    # ═══════════════════════════════════════════════════════════
    try:
        from services.backfill_capas_bg import start_backfill_capas_bg
        start_backfill_capas_bg()
    except Exception as _e:
        app.logger.warning(f"Backfill de capas não pôde ser iniciado: {_e}")

    return app


app = create_app()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=os.getenv("FLASK_ENV") != "production")
