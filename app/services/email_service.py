import smtplib
from email.message import EmailMessage

from flask import current_app


def send_email(to_email: str, subject: str, body: str, html_body: str | None = None) -> bool:
    to_value = (to_email or "").strip()
    if not to_value:
        current_app.logger.warning("Email no enviado: destinatario vacio")
        return False

    if current_app.config.get("MAIL_SUPPRESS_SEND", False):
        current_app.logger.info(
            "Email suprimido por config MAIL_SUPPRESS_SEND para %s", to_value
        )
        return True

    smtp_host = (current_app.config.get("SMTP_HOST") or "").strip()
    smtp_port = int(current_app.config.get("SMTP_PORT") or 587)
    smtp_user = (current_app.config.get("SMTP_USER") or "").strip()
    smtp_password = current_app.config.get("SMTP_PASSWORD") or ""
    smtp_use_tls = bool(current_app.config.get("SMTP_USE_TLS", True))
    smtp_use_ssl = bool(current_app.config.get("SMTP_USE_SSL", False))
    mail_from = (
        (current_app.config.get("MAIL_FROM") or "").strip() or smtp_user or ""
    )
    timeout_seconds = int(current_app.config.get("MAIL_TIMEOUT_SECONDS") or 10)

    if not smtp_host or not mail_from:
        current_app.logger.warning(
            "Email no enviado: falta SMTP_HOST o MAIL_FROM (to=%s)", to_value
        )
        return False

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = mail_from
    message["To"] = to_value
    message.set_content(body)
    if html_body:
        message.add_alternative(html_body, subtype="html")

    try:
        if smtp_use_ssl:
            smtp_client = smtplib.SMTP_SSL(
                host=smtp_host,
                port=smtp_port,
                timeout=timeout_seconds,
            )
        else:
            smtp_client = smtplib.SMTP(
                host=smtp_host,
                port=smtp_port,
                timeout=timeout_seconds,
            )

        with smtp_client as client:
            client.ehlo()
            if smtp_use_tls and not smtp_use_ssl:
                client.starttls()
                client.ehlo()
            if smtp_user:
                client.login(smtp_user, smtp_password)
            client.send_message(message)
    except Exception:
        current_app.logger.exception("Error al enviar email a %s", to_value)
        return False

    return True
