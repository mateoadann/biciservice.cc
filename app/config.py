import os
from datetime import timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    value = os.environ.get(name)
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-change-me")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "postgresql+psycopg://postgres:postgres@localhost:5432/service_bicycle_crm",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.environ.get(
        "UPLOAD_FOLDER", str(BASE_DIR / "app" / "static" / "uploads")
    )
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024
    ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "svg", "ico"}
    SESSION_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = _env_bool("SESSION_COOKIE_SECURE", False)
    REMEMBER_COOKIE_SECURE = _env_bool("REMEMBER_COOKIE_SECURE", False)
    SECURITY_EMAIL_CONFIRM_EXPIRES = 60 * 60
    APP_BASE_URL = os.environ.get("APP_BASE_URL", "").strip()
    MAIL_FROM = os.environ.get("MAIL_FROM", "").strip()
    SMTP_HOST = os.environ.get("SMTP_HOST", "").strip()
    SMTP_PORT = _env_int("SMTP_PORT", 587)
    SMTP_USER = os.environ.get("SMTP_USER", "").strip()
    SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
    SMTP_USE_TLS = _env_bool("SMTP_USE_TLS", True)
    SMTP_USE_SSL = _env_bool("SMTP_USE_SSL", False)
    MAIL_TIMEOUT_SECONDS = _env_int("MAIL_TIMEOUT_SECONDS", 10)
    MAIL_SUPPRESS_SEND = _env_bool("MAIL_SUPPRESS_SEND", False)
    ADMIN_NOTIFICATION_EMAIL = os.environ.get("ADMIN_NOTIFICATION_EMAIL", "").strip()
    LOGIN_RATE_LIMIT_WINDOW = 300
    LOGIN_RATE_LIMIT_MAX = 5
    SECURITY_PASSWORD_RESET_EXPIRES = 60 * 60
    SECURITY_TWO_FACTOR_ISSUER = "Service Bicycle CRM"
    LOGIN_LOCKOUT_MAX = 5
    LOGIN_LOCKOUT_DURATION = 900
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    REMEMBER_COOKIE_DURATION = timedelta(days=14)
    SESSION_REFRESH_EACH_REQUEST = False
