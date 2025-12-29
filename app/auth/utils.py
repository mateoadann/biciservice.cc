from datetime import datetime

from flask import current_app, url_for
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer


def _serializer():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"])


def generate_confirmation_token(email: str) -> str:
    return _serializer().dumps(email, salt="email-confirm")


def confirm_email_token(token: str, expires_in: int) -> str | None:
    try:
        return _serializer().loads(token, salt="email-confirm", max_age=expires_in)
    except (SignatureExpired, BadSignature):
        return None


def send_confirmation_email(user) -> None:
    token = generate_confirmation_token(user.email)
    confirm_url = url_for("auth.confirm_email", token=token, _external=True)
    current_app.logger.info("Confirm email for %s: %s", user.email, confirm_url)
    user.confirmation_sent_at = datetime.utcnow()
