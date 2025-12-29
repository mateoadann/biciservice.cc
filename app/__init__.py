import os
from decimal import Decimal, InvalidOperation
from flask import Flask, g, request, session, url_for, flash
from flask_login import current_user
from werkzeug.middleware.proxy_fix import ProxyFix
from dotenv import load_dotenv
from flask_wtf.csrf import CSRFError

from .config import Config
from .extensions import csrf, db, login_manager, migrate
from .models import User, Workshop


def create_app(config_class=Config):
    load_dotenv()
    app = Flask(__name__)
    app.config.from_object(config_class)

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    login_manager.login_view = "auth.login"
    login_manager.login_message = "Inicia sesion para continuar."

    from .auth.routes import auth_bp
    from .main.routes import main_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    @app.before_request
    def set_active_workshop():
        g.active_workshop = None
        if not current_user.is_authenticated:
            return
        workshop_id = session.get("active_workshop_id")
        if workshop_id:
            g.active_workshop = db.session.get(Workshop, workshop_id)
        if g.active_workshop is None and current_user.workshops:
            g.active_workshop = current_user.workshops[0]
            session["active_workshop_id"] = g.active_workshop.id

    @app.context_processor
    def inject_theme():
        default_theme = {
            "primary": "#1f4cff",
            "secondary": "#19b36b",
            "accent": "#ff8c2b",
            "background": "#f6f7fb",
            "logo_path": None,
            "favicon_path": None,
            "name": "Service Bicycle CRM",
        }
        if g.get("active_workshop"):
            theme = g.active_workshop.theme()
        else:
            theme = default_theme
        return {"theme": theme}

    @app.after_request
    def apply_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=()"
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "img-src 'self' data:; "
            "style-src 'self' https://fonts.googleapis.com 'unsafe-inline'; "
            "font-src 'self' https://fonts.gstatic.com; "
            "script-src 'self' 'unsafe-inline'"
        )
        if request.is_secure:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

    @app.errorhandler(CSRFError)
    def handle_csrf_error(error):
        flash("La sesion expiro. Intenta de nuevo.", "error")
        return redirect(request.referrer or url_for("auth.login")), 400

    def format_currency(value):
        if value is None:
            return "-"
        try:
            if isinstance(value, Decimal):
                numeric = value
            else:
                numeric = Decimal(str(value))
            formatted = f"{numeric:,.2f}"
        except (InvalidOperation, ValueError, TypeError):
            return str(value)
        return formatted.replace(",", "X").replace(".", ",").replace("X", ".")

    app.jinja_env.filters["currency"] = format_currency

    return app
