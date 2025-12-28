import os
from flask import Flask, g, session
from flask_login import current_user
from werkzeug.middleware.proxy_fix import ProxyFix
from dotenv import load_dotenv

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
    login_manager.login_message = "Please log in to continue."

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

    return app
