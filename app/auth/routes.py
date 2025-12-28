from flask import flash, redirect, render_template, request, session, url_for
from flask_login import login_required, login_user, logout_user
from flask_wtf import FlaskForm
from wtforms import BooleanField, PasswordField, StringField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError

from . import auth_bp
from ..extensions import db
from ..models import User, Workshop


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    remember = BooleanField("Remember me")


class RegisterForm(FlaskForm):
    full_name = StringField("Full name", validators=[DataRequired(), Length(max=120)])
    email = StringField("Email", validators=[DataRequired(), Email()])
    workshop_name = StringField(
        "Workshop name", validators=[DataRequired(), Length(max=120)]
    )
    password = PasswordField(
        "Password", validators=[DataRequired(), Length(min=8, max=64)]
    )
    confirm = PasswordField(
        "Confirm password",
        validators=[DataRequired(), EqualTo("password", message="Passwords must match")],
    )

    def validate_email(self, field):
        if User.query.filter_by(email=field.data.lower()).first():
            raise ValidationError("Email is already registered")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        if not user or not user.check_password(form.password.data):
            flash("Invalid email or password", "error")
            return render_template("auth/login.html", form=form)
        login_user(user, remember=form.remember.data)
        if user.workshops:
            session["active_workshop_id"] = user.workshops[0].id
        return redirect(url_for("main.dashboard"))
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
        login_user(user)
        session["active_workshop_id"] = workshop.id
        return redirect(url_for("main.dashboard"))
    return render_template("auth/register.html", form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    session.pop("active_workshop_id", None)
    return redirect(url_for("auth.login"))
