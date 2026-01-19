from datetime import datetime, timezone

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
    message = f"Confirm email for {user.email}: {confirm_url}"
    current_app.logger.warning(message)
    print(message, flush=True)
    user.confirmation_sent_at = datetime.now(timezone.utc)


def send_password_reset_email(user, token: str) -> None:
    reset_url = url_for(
        "auth.reset_password", user_id=user.id, token=token, _external=True
    )
    message = f"Reset password for {user.email}: {reset_url}"
    current_app.logger.warning(message)
    print(message, flush=True)
