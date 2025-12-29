from datetime import datetime, timedelta
from time import time

from flask import current_app, flash, redirect, render_template, request, session, url_for
from flask_login import login_required, login_user, logout_user
from flask_wtf import FlaskForm
from wtforms import BooleanField, PasswordField, StringField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError

from . import auth_bp
from .utils import confirm_email_token, send_confirmation_email
from ..config import Config
from ..extensions import db
from ..models import User, Workshop


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
    return datetime.utcnow() - user.confirmation_sent_at > timedelta(minutes=5)


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
        if not user or not user.check_password(form.password.data):
            _record_attempt(key)
            flash("Email o contrasena incorrectos", "error")
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
        login_user(user, remember=form.remember.data)
        if user.workshops:
            session["active_workshop_id"] = user.workshops[0].id
        return redirect(url_for("main.dashboard"))
    if request.method == "POST":
        flash("Revisa los datos ingresados", "error")
    return render_template("auth/login.html", form=form)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        workshop = Workshop(name=form.workshop_name.data)
        user = User(full_name=form.full_name.data, email=form.email.data.lower())
        user.set_password(form.password.data)
        user.workshops.append(workshop)
        db.session.add_all([user, workshop])
        db.session.commit()
        send_confirmation_email(user)
        db.session.commit()
        flash("Te enviamos un correo para verificar tu cuenta.", "success")
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
    user.email_confirmed_at = datetime.utcnow()
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


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    session.pop("active_workshop_id", None)
    return redirect(url_for("auth.login"))
