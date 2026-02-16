from datetime import datetime, timezone

from flask import current_app, render_template, url_for
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.services.email_service import send_email


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
    full_name = user.full_name or "cliente"
    token = generate_confirmation_token(user.email)
    confirm_url = url_for("auth.confirm_email", token=token, _external=True)
    expires_minutes = int(current_app.config.get("SECURITY_EMAIL_CONFIRM_EXPIRES", 3600) / 60)
    subject = "Confirma tu cuenta - biciservice.cc"
    body = (
        f"Hola {full_name},\n\n"
        "Para confirmar tu email y activar tu cuenta, usa este link:\n"
        f"{confirm_url}\n\n"
        f"Este link vence en {expires_minutes} minutos.\n"
        "Si no solicitaste este registro, ignora este correo.\n"
    )
    html_body = render_template(
        "emails/confirmation_email.html",
        full_name=full_name,
        confirm_url=confirm_url,
        expires_minutes=expires_minutes,
    )
    sent = send_email(user.email, subject, body, html_body=html_body)
    if sent:
        user.confirmation_sent_at = datetime.now(timezone.utc)
    else:
        current_app.logger.warning(
            "No se pudo enviar confirmacion a %s. Link generado: %s",
            user.email,
            confirm_url,
        )


def send_approval_notification(user) -> None:
    full_name = user.full_name or "cliente"
    login_url = url_for("auth.login", _external=True)
    subject = "Tu cuenta fue aprobada"
    body = (
        f"Hola {full_name},\n\n"
        "Tu cuenta ya fue aprobada por el administrador.\n"
        "Puedes iniciar sesion desde este link:\n"
        f"{login_url}\n"
    )
    html_body = render_template(
        "emails/approval_email.html",
        full_name=full_name,
        login_url=login_url,
    )
    sent = send_email(user.email, subject, body, html_body=html_body)
    if not sent:
        current_app.logger.warning(
            "No se pudo enviar aviso de aprobacion a %s. Link: %s",
            user.email,
            login_url,
        )


def notify_admin_new_registration(user) -> None:
    admin_email = (current_app.config.get("ADMIN_NOTIFICATION_EMAIL") or "").strip()
    if not admin_email:
        current_app.logger.warning(
            "ADMIN_NOTIFICATION_EMAIL no configurado. Registro pendiente: %s",
            user.email,
        )
        return

    pending_url = url_for("main.super_admin_pending", _external=True)
    subject = "Nuevo registro pendiente de aprobacion"
    body = (
        "Se registro un nuevo owner pendiente de aprobacion.\n\n"
        f"Email: {user.email}\n"
        f"Nombre: {user.full_name}\n"
        f"Panel de pendientes: {pending_url}\n"
    )
    sent = send_email(admin_email, subject, body)
    if not sent:
        current_app.logger.warning(
            "No se pudo enviar aviso de registro pendiente a %s",
            admin_email,
        )


def send_password_reset_email(user, token: str) -> None:
    full_name = user.full_name or "cliente"
    reset_url = url_for(
        "auth.reset_password", user_id=user.id, token=token, _external=True
    )
    expires_minutes = int(current_app.config.get("SECURITY_PASSWORD_RESET_EXPIRES", 3600) / 60)
    subject = "Recuperacion de contrasena - biciservice.cc"
    body = (
        f"Hola {full_name},\n\n"
        "Recibimos una solicitud para restablecer tu contrasena.\n"
        "Usa este link para continuar:\n"
        f"{reset_url}\n\n"
        f"Este link vence en {expires_minutes} minutos.\n"
        "Si no solicitaste este cambio, ignora este correo.\n"
    )
    html_body = render_template(
        "emails/reset_password_email.html",
        full_name=full_name,
        reset_url=reset_url,
        expires_minutes=expires_minutes,
    )
    sent = send_email(user.email, subject, body, html_body=html_body)
    if not sent:
        current_app.logger.warning(
            "No se pudo enviar reset de contrasena a %s. Link: %s",
            user.email,
            reset_url,
        )
