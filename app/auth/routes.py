from datetime import datetime, timedelta, timezone
import math
import pyotp
from time import time

from flask import current_app, flash, redirect, render_template, request, session, url_for
from flask_login import login_required, login_user, logout_user
from flask_wtf import FlaskForm
from wtforms import BooleanField, PasswordField, StringField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Regexp, ValidationError

from . import auth_bp
from .utils import (
    confirm_email_token,
    notify_admin_new_registration,
    send_confirmation_email,
    send_password_reset_email,
)
from ..config import Config
from ..extensions import db
from ..models import User, Workshop, Store


class LoginForm(FlaskForm):
    email = StringField(
        "Email",
        validators=[
            DataRequired(message="Campo obligatorio"),
            Email(message="Email invalido"),
        ],
    )
    password = PasswordField(
        "Password", validators=[DataRequired(message="Campo obligatorio")]
    )
    remember = BooleanField("Remember me")


class RegisterForm(FlaskForm):
    full_name = StringField(
        "Full name", validators=[DataRequired(message="Campo obligatorio"), Length(max=120)]
    )
    email = StringField(
        "Email",
        validators=[
            DataRequired(message="Campo obligatorio"),
            Email(message="Email invalido"),
        ],
    )
    workshop_name = StringField(
        "Workshop name",
        validators=[DataRequired(message="Campo obligatorio"), Length(max=120)],
    )
    password = PasswordField(
        "Password",
        validators=[DataRequired(message="Campo obligatorio"), Length(min=8, max=64)],
    )
    confirm = PasswordField(
        "Confirm password",
        validators=[
            DataRequired(message="Campo obligatorio"),
            EqualTo("password", message="Las contrasenas no coinciden"),
        ],
    )

    def validate_email(self, field):
        if User.query.filter_by(email=field.data.lower()).first():
            raise ValidationError("El email ya esta registrado")

    def validate_password(self, field):
        password = field.data or ""
        if (
            not any(char.islower() for char in password)
            or not any(char.isupper() for char in password)
            or not any(char.isdigit() for char in password)
        ):
            raise ValidationError(
                "La contrasena debe incluir mayuscula, minuscula y numero"
            )


class ResendConfirmationForm(FlaskForm):
    email = StringField(
        "Email",
        validators=[
            DataRequired(message="Campo obligatorio"),
            Email(message="Email invalido"),
        ],
    )


class ForgotPasswordForm(FlaskForm):
    email = StringField(
        "Email",
        validators=[
            DataRequired(message="Campo obligatorio"),
            Email(message="Email invalido"),
        ],
    )


class ResetPasswordForm(FlaskForm):
    password = PasswordField(
        "Password",
        validators=[DataRequired(message="Campo obligatorio"), Length(min=8, max=64)],
    )
    confirm = PasswordField(
        "Confirm password",
        validators=[
            DataRequired(message="Campo obligatorio"),
            EqualTo("password", message="Las contrasenas no coinciden"),
        ],
    )

    def validate_password(self, field):
        password = field.data or ""
        if (
            not any(char.islower() for char in password)
            or not any(char.isupper() for char in password)
            or not any(char.isdigit() for char in password)
        ):
            raise ValidationError(
                "La contrasena debe incluir mayuscula, minuscula y numero"
            )



class TwoFactorForm(FlaskForm):
    code = StringField(
        "Codigo",
        validators=[
            DataRequired(message="Campo obligatorio"),
            Length(min=6, max=6),
            Regexp(r"^\d{6}$", message="Codigo invalido"),
        ],
    )


_login_attempts = {}


def _rate_limit_key(email: str) -> str:
    ip = request.headers.get("X-Forwarded-For", request.remote_addr) or "unknown"
    return f"{ip}:{email}"


def _is_rate_limited(key: str) -> bool:
    now = time()
    window = current_app.config["LOGIN_RATE_LIMIT_WINDOW"]
    attempts = [ts for ts in _login_attempts.get(key, []) if now - ts < window]
    _login_attempts[key] = attempts
    return len(attempts) >= current_app.config["LOGIN_RATE_LIMIT_MAX"]


def _record_attempt(key: str, success: bool = False) -> None:
    if success:
        _login_attempts.pop(key, None)
        return
    now = time()
    attempts = _login_attempts.get(key, [])
    attempts.append(now)
    _login_attempts[key] = attempts


def _can_resend_confirmation(user) -> bool:
    if not user.confirmation_sent_at:
        return True
    return datetime.now(timezone.utc) - user.confirmation_sent_at > timedelta(minutes=5)



def _lockout_remaining(user) -> int | None:
    if not user.locked_until:
        return None
    now = datetime.now(timezone.utc)
    if user.locked_until <= now:
        user.locked_until = None
        user.failed_login_attempts = 0
        db.session.commit()
        return None
    return int((user.locked_until - now).total_seconds())


def _register_failed_login(user) -> bool:
    user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
    max_attempts = current_app.config["LOGIN_LOCKOUT_MAX"]
    if user.failed_login_attempts >= max_attempts:
        user.failed_login_attempts = 0
        user.locked_until = datetime.now(timezone.utc) + timedelta(
            seconds=current_app.config["LOGIN_LOCKOUT_DURATION"]
        )
        db.session.commit()
        return True
    db.session.commit()
    return False


def _reset_lockout(user) -> None:
    if user.failed_login_attempts or user.locked_until:
        user.failed_login_attempts = 0
        user.locked_until = None
        db.session.commit()



def _post_login_redirect(user):
    _reset_lockout(user)
    if user.role == "super_admin":
        return redirect(url_for("main.super_admin_dashboard"))
    if user.workshops:
        workshop = user.workshops[0]
        session["active_workshop_id"] = workshop.id
        if user.role != "owner" and user.store_id:
            session["active_store_id"] = user.store_id
        else:
            store = (
                Store.query.filter_by(workshop_id=workshop.id)
                .order_by(Store.id.asc())
                .first()
            )
            if store:
                session["active_store_id"] = store.id
    return redirect(url_for("main.dashboard"))


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data.lower()
        key = _rate_limit_key(email)
        if _is_rate_limited(key):
            flash("Demasiados intentos. Intenta mas tarde.", "error")
            return render_template("auth/login.html", form=form)

        user = User.query.filter_by(email=email).first()
        if user:
            remaining = _lockout_remaining(user)
            if remaining:
                minutes = max(1, math.ceil(remaining / 60))
                flash(f"Cuenta bloqueada. Intenta en {minutes} min.", "error")
                return render_template("auth/login.html", form=form)

        if not user or not user.check_password(form.password.data):
            _record_attempt(key)
            if user:
                locked = _register_failed_login(user)
                if locked:
                    flash(
                        "Cuenta bloqueada por intentos fallidos. Intenta mas tarde.",
                        "error",
                    )
                    return render_template("auth/login.html", form=form)
            flash("Email o contrasena incorrectos", "error")
            return render_template("auth/login.html", form=form)
        if not user.is_active:
            flash("Cuenta desactivada. Contacta al administrador.", "error")
            return render_template("auth/login.html", form=form)
        if not user.is_approved:
            flash("Tu cuenta esta pendiente de aprobacion por el administrador.", "error")
            return render_template("auth/login.html", form=form)
        if user.email_confirmed is False:
            if _can_resend_confirmation(user):
                send_confirmation_email(user)
                db.session.commit()
                flash("Email sin confirmar. Te enviamos un nuevo link.", "error")
            else:
                flash("Email sin confirmar. Revisa tu correo.", "error")
            return render_template("auth/login.html", form=form)
        _record_attempt(key, success=True)
        if user.two_factor_enabled and user.two_factor_secret:
            session["pending_2fa_user_id"] = user.id
            session["pending_2fa_remember"] = bool(form.remember.data)
            session.permanent = True
            return redirect(url_for("auth.login_two_factor"))
        login_user(user, remember=form.remember.data)
        session.permanent = True
        return _post_login_redirect(user)
    if request.method == "POST":
        flash("Revisa los datos ingresados", "error")
    return render_template("auth/login.html", form=form)




@auth_bp.route("/login/2fa", methods=["GET", "POST"])
def login_two_factor():
    user_id = session.get("pending_2fa_user_id")
    if not user_id:
        flash("Sesion invalida. Ingresa de nuevo.", "error")
        return redirect(url_for("auth.login"))
    user = db.session.get(User, int(user_id))
    if not user or not user.two_factor_enabled or not user.two_factor_secret:
        session.pop("pending_2fa_user_id", None)
        session.pop("pending_2fa_remember", None)
        flash("Sesion invalida. Ingresa de nuevo.", "error")
        return redirect(url_for("auth.login"))
    if not user.is_active:
        session.pop("pending_2fa_user_id", None)
        session.pop("pending_2fa_remember", None)
        flash("Cuenta desactivada. Contacta al administrador.", "error")
        return redirect(url_for("auth.login"))
    if not user.is_approved:
        session.pop("pending_2fa_user_id", None)
        session.pop("pending_2fa_remember", None)
        flash("Tu cuenta esta pendiente de aprobacion por el administrador.", "error")
        return redirect(url_for("auth.login"))
    form = TwoFactorForm()
    if form.validate_on_submit():
        totp = pyotp.TOTP(user.two_factor_secret)
        if not totp.verify(form.code.data, valid_window=1):
            flash("Codigo incorrecto.", "error")
            return render_template("auth/2fa.html", form=form)
        remember = session.pop("pending_2fa_remember", False)
        session.pop("pending_2fa_user_id", None)
        login_user(user, remember=bool(remember))
        session.permanent = True
        return _post_login_redirect(user)
    if request.method == "POST":
        flash("Revisa los datos ingresados", "error")
    return render_template("auth/2fa.html", form=form)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        workshop = Workshop(name=form.workshop_name.data)
        store = Store(name="Sucursal principal", workshop=workshop)
        user = User(
            full_name=form.full_name.data,
            email=form.email.data.lower(),
            role="owner",
            store=store,
        )
        user.set_password(form.password.data)
        user.workshops.append(workshop)
        db.session.add_all([user, workshop, store])
        db.session.commit()
        send_confirmation_email(user)
        notify_admin_new_registration(user)
        db.session.commit()
        flash(
            "Te enviamos un correo para verificar tu cuenta. Un administrador debe aprobar tu registro.",
            "success",
        )
        return redirect(url_for("auth.login"))
    if request.method == "POST":
        flash("Revisa los datos ingresados", "error")
    return render_template("auth/register.html", form=form)


@auth_bp.route("/confirm/<token>")
def confirm_email(token):
    email = confirm_email_token(token, Config.SECURITY_EMAIL_CONFIRM_EXPIRES)
    if not email:
        flash("Link expirado o invalido.", "error")
        return redirect(url_for("auth.login"))

    user = User.query.filter_by(email=email.lower()).first()
    if not user:
        flash("Cuenta no encontrada.", "error")
        return redirect(url_for("auth.register"))
    if user.email_confirmed:
        flash("Tu email ya esta confirmado.", "success")
        return redirect(url_for("auth.login"))

    user.email_confirmed = True
    user.email_confirmed_at = datetime.now(timezone.utc)
    db.session.commit()
    flash("Email confirmado. Ya puedes iniciar sesion.", "success")
    return redirect(url_for("auth.login"))


@auth_bp.route("/resend-confirmation", methods=["GET", "POST"])
def resend_confirmation():
    form = ResendConfirmationForm()
    if form.validate_on_submit():
        email = form.email.data.lower()
        user = User.query.filter_by(email=email).first()
        if user and user.email_confirmed is False and _can_resend_confirmation(user):
            send_confirmation_email(user)
            db.session.commit()
        flash("Si la cuenta existe, enviamos un nuevo link.", "success")
        return redirect(url_for("auth.login"))
    if request.method == "POST":
        flash("Revisa los datos ingresados", "error")
    return render_template("auth/resend.html", form=form)




@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        email = form.email.data.lower()
        user = User.query.filter_by(email=email).first()
        if user and user.is_active:
            token = user.set_password_reset_token(
                current_app.config["SECURITY_PASSWORD_RESET_EXPIRES"]
            )
            send_password_reset_email(user, token)
            db.session.commit()
        flash("Si la cuenta existe, enviamos un link para resetear la contrasena.", "success")
        return redirect(url_for("auth.login"))
    if request.method == "POST":
        flash("Revisa los datos ingresados", "error")
    return render_template("auth/forgot_password.html", form=form)


@auth_bp.route("/reset-password/<int:user_id>/<token>", methods=["GET", "POST"])
def reset_password(user_id, token):
    user = User.query.filter_by(id=user_id).first()
    if not user or not user.verify_password_reset_token(token):
        flash("Link expirado o invalido.", "error")
        return redirect(url_for("auth.login"))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        user.clear_password_reset_token()
        user.failed_login_attempts = 0
        user.locked_until = None
        db.session.commit()
        flash("Contrasena actualizada. Ingresa con la nueva clave.", "success")
        return redirect(url_for("auth.login"))
    if request.method == "POST":
        flash("Revisa los datos ingresados", "error")
    return render_template("auth/reset_password.html", form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    session.pop("active_workshop_id", None)
    session.pop("active_store_id", None)
    session.pop("pending_2fa_user_id", None)
    session.pop("pending_2fa_remember", None)
    session.pop("two_factor_pending_secret", None)
    return redirect(url_for("auth.login"))
