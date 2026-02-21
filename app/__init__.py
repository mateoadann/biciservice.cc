import click
import logging
import os
from decimal import Decimal, InvalidOperation
from datetime import datetime, timezone
from flask import (
    Flask,
    g,
    request,
    session,
    url_for,
    flash,
    redirect,
    render_template,
    send_from_directory,
)
from flask_login import current_user
from werkzeug.middleware.proxy_fix import ProxyFix
from dotenv import load_dotenv
from flask_wtf.csrf import CSRFError

from .config import Config
from .extensions import csrf, db, login_manager, migrate
from .models import User, Workshop, Store


def create_app(config_class=Config):
    load_dotenv()
    app = Flask(__name__)
    app.config.from_object(config_class)

    if not app.debug and not app.testing:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        )

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    login_manager.login_view = "auth.login"
    login_manager.login_message = "Inicia sesion para continuar."
    login_manager.session_protection = "strong"

    from .auth.routes import auth_bp
    from .main import main_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)

    @app.get("/health")
    def health_check():
        return "ok", 200

    @app.get("/manifest.webmanifest")
    def manifest_file():
        response = send_from_directory(
            app.static_folder,
            "manifest.webmanifest",
            mimetype="application/manifest+json",
        )
        response.headers["Cache-Control"] = "no-cache"
        return response

    @app.get("/sw.js")
    def service_worker_file():
        response = app.response_class(
            render_template(
                "sw.js.j2",
                asset_version=app.config["ASSET_VERSION"],
            ),
            mimetype="application/javascript",
        )
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        return response

    @app.get("/app.css")
    def app_css_file():
        response = app.response_class(
            render_template(
                "app.css.j2",
                asset_version=app.config["ASSET_VERSION"],
            ),
            mimetype="text/css",
        )
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        return response

    @app.get("/apple-touch-icon.png")
    def apple_touch_icon():
        return send_from_directory(
            app.static_folder,
            "icons/apple-touch-icon-180.png",
            mimetype="image/png",
        )

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    @app.before_request
    def set_active_workshop():
        g.active_workshop = None
        g.active_store = None
        g.workshop_stores = []
        if not current_user.is_authenticated:
            return
        if current_user.role == "super_admin":
            return
        workshop_id = session.get("active_workshop_id")
        if workshop_id:
            g.active_workshop = db.session.get(Workshop, workshop_id)
        if g.active_workshop is None and current_user.workshops:
            g.active_workshop = current_user.workshops[0]
            session["active_workshop_id"] = g.active_workshop.id

        if g.active_workshop is None:
            return

        g.workshop_stores = (
            Store.query.filter_by(workshop_id=g.active_workshop.id)
            .order_by(Store.name.asc())
            .all()
        )

        active_store_id = session.get("active_store_id")
        store = None
        if active_store_id:
            store = next((s for s in g.workshop_stores if s.id == active_store_id), None)

        if current_user.role != "owner":
            if current_user.store_id:
                store = next(
                    (s for s in g.workshop_stores if s.id == current_user.store_id),
                    None,
                )
            else:
                store = None
            if store:
                session["active_store_id"] = store.id
            else:
                session.pop("active_store_id", None)
        else:
            if store is None:
                store = min(g.workshop_stores, key=lambda s: s.id, default=None)
                if store:
                    session["active_store_id"] = store.id

        g.active_store = store

    @app.context_processor
    def inject_theme():
        default_theme = {
            "primary": "#1f4cff",
            "secondary": "#19b36b",
            "accent": "#ff8c2b",
            "background": "#f6f7fb",
            "logo_path": None,
            "favicon_path": None,
            "name": "biciservice.cc",
        }
        stores = []
        if g.get("active_workshop"):
            theme = g.active_workshop.theme()
            stores = g.get("workshop_stores", [])
        else:
            theme = default_theme
        asset_version = app.config["ASSET_VERSION"]

        def asset_url(path: str) -> str:
            if path == "css/app.css":
                return url_for("app_css_file", v=asset_version)
            return url_for("static", filename=path, v=asset_version)

        return {
            "theme": theme,
            "stores": stores,
            "active_store": g.get("active_store"),
            "asset_version": asset_version,
            "asset_url": asset_url,
        }

    @app.after_request
    def apply_security_headers(response):
        if request.path.startswith("/static/"):
            response.headers["Cache-Control"] = "public, max-age=31536000"

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=()"
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "img-src 'self' data:; "
            "style-src 'self' 'unsafe-inline'; "
            "font-src 'self'; "
            "script-src 'self' 'unsafe-inline'"
        )
        if request.is_secure:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

    @app.errorhandler(CSRFError)
    def handle_csrf_error(error):
        flash("La sesion expiro. Intenta de nuevo.", "error")
        return redirect(request.referrer or url_for("auth.login")), 400

    @app.errorhandler(404)
    def not_found(error):
        app.logger.info("404 %s %s", request.method, request.path)
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error("500 %s %s", request.method, request.path, exc_info=True)
        db.session.rollback()
        return render_template("errors/500.html"), 500

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

    @app.cli.command("create-superadmin")
    @click.option("--email", prompt=True)
    @click.option("--name", prompt=True)
    @click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
    def create_superadmin(email, name, password):
        """Crea un usuario super_admin."""
        email_value = email.strip().lower()
        existing_super = User.query.filter_by(role="super_admin").first()
        if existing_super:
            click.echo("Ya existe un super admin")
            return
        existing = User.query.filter_by(email=email_value).first()
        if existing:
            click.echo("El email ya existe")
            return
        user = User(
            full_name=name.strip(),
            email=email_value,
            role="super_admin",
            store_id=None,
            is_approved=True,
            approved_at=datetime.now(timezone.utc),
            email_confirmed=True,
            email_confirmed_at=datetime.now(timezone.utc),
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        click.echo("Super admin creado")

    @app.cli.command("send-test-email")
    @click.option("--to", prompt="Email destino de prueba")
    def send_test_email(to):
        """Envia un correo de prueba con la config SMTP actual."""
        from .services.email_service import send_email

        to_value = to.strip().lower()
        subject = "Prueba de correo - biciservice.cc"
        timestamp = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")
        body_lines = [
            "Este es un correo de prueba de biciservice.cc.",
            "",
            "Si recibiste este correo, la configuracion SMTP funciona.",
            f"Fecha: {timestamp}",
        ]
        if app.config.get("APP_BASE_URL"):
            body_lines.append(f"URL de app configurada: {app.config['APP_BASE_URL']}")

        sent = send_email(to_value, subject, "\n".join(body_lines))
        if not sent:
            raise click.ClickException(
                "No se pudo enviar el correo de prueba. Revisa SMTP_* y MAIL_FROM en .env"
            )

        click.echo(f"Correo de prueba enviado a {to_value}")

    app.jinja_env.filters["currency"] = format_currency

    return app
