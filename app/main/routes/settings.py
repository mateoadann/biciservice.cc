import pyotp
from flask import render_template, request, redirect, url_for, flash, session, current_app
from flask_login import login_required, current_user
from app.main import main_bp
from app.extensions import db
from app.services.audit_service import AuditService
from app.main.forms import WorkshopSettingsForm, DeleteForm, TwoFactorSetupForm, TwoFactorDisableForm
from app.main.helpers import (
    get_workshop_or_redirect,
    owner_or_redirect,
    save_upload,
    delete_upload
)

@main_bp.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    workshop, redirect_response = get_workshop_or_redirect()
    if redirect_response:
        return redirect_response

    _, owner_redirect = owner_or_redirect()
    if owner_redirect:
        return owner_redirect

    form = WorkshopSettingsForm()
    if request.method == "GET":
        form.name.data = workshop.name
        form.primary_color.data = workshop.primary_color
        form.secondary_color.data = workshop.secondary_color
        form.accent_color.data = workshop.accent_color
        form.background_color.data = workshop.background_color

    if form.validate_on_submit():
        workshop.name = form.name.data
        workshop.primary_color = form.primary_color.data or workshop.primary_color
        workshop.secondary_color = form.secondary_color.data or workshop.secondary_color
        workshop.accent_color = form.accent_color.data or workshop.accent_color
        workshop.background_color = form.background_color.data or workshop.background_color

        logo_path, logo_error = save_upload(form.logo.data, workshop.id)
        if logo_error:
            flash(logo_error, "error")
            return redirect(url_for("main.settings"))
        if logo_path:
            if workshop.logo_path and workshop.logo_path != logo_path:
                delete_upload(workshop.logo_path)
            workshop.logo_path = logo_path

        favicon_path, favicon_error = save_upload(form.favicon.data, workshop.id)
        if favicon_error:
            flash(favicon_error, "error")
            return redirect(url_for("main.settings"))
        if favicon_path:
            if workshop.favicon_path and workshop.favicon_path != favicon_path:
                delete_upload(workshop.favicon_path)
            workshop.favicon_path = favicon_path

        AuditService.log_action(
            "update",
            "workshop",
            workshop.id,
            "Actualizo configuracion del taller",
            workshop_id=workshop.id,
        )
        db.session.commit()
        flash("Configuracion del taller actualizada", "success")
        return redirect(url_for("main.settings"))

    if request.method == "POST" and form.errors:
        flash("Revisa los campos ingresados", "error")
    return render_template("main/settings.html", form=form, workshop=workshop)


@main_bp.route("/security", methods=["GET", "POST"])
@login_required
def security():
    setup_form = TwoFactorSetupForm()
    disable_form = TwoFactorDisableForm()
    pending_secret = session.get("two_factor_pending_secret")
    setup_uri = None

    if current_user.two_factor_enabled:
        session.pop("two_factor_pending_secret", None)
    else:
        if not pending_secret:
            pending_secret = pyotp.random_base32()
            session["two_factor_pending_secret"] = pending_secret
        setup_uri = pyotp.totp.TOTP(pending_secret).provisioning_uri(
            name=current_user.email,
            issuer_name=current_app.config.get("SECURITY_TWO_FACTOR_ISSUER", "Service Bicycle CRM"),
        )

    if request.method == "POST":
        form_name = request.form.get("form_name")
        if form_name == "enable_2fa":
            if not setup_form.validate_on_submit():
                flash("Revisa los datos ingresados", "error")
            else:
                secret = session.get("two_factor_pending_secret")
                if not secret:
                    flash("Sesion invalida. Reintenta.", "error")
                else:
                    totp = pyotp.TOTP(secret)
                    if not totp.verify(setup_form.code.data, valid_window=1):
                        flash("Codigo incorrecto.", "error")
                    else:
                        current_user.two_factor_secret = secret
                        current_user.two_factor_enabled = True
                        session.pop("two_factor_pending_secret", None)
                        db.session.commit()
                        flash("2FA activado.", "success")
                        return redirect(url_for("main.security"))
        elif form_name == "disable_2fa":
            if not disable_form.validate_on_submit():
                flash("Revisa los datos ingresados", "error")
            elif not current_user.check_password(disable_form.password.data):
                flash("Password incorrecto.", "error")
            else:
                current_user.two_factor_enabled = False
                current_user.two_factor_secret = None
                db.session.commit()
                flash("2FA desactivado.", "success")
                return redirect(url_for("main.security"))

    return render_template(
        "main/security.html",
        setup_form=setup_form,
        disable_form=disable_form,
        setup_uri=setup_uri,
        setup_secret=pending_secret,
    )


@main_bp.route("/settings/remove-logo", methods=["POST"])
@login_required
def settings_remove_logo():
    workshop, redirect_response = get_workshop_or_redirect()
    if redirect_response:
        return redirect_response

    _, owner_redirect = owner_or_redirect()
    if owner_redirect:
        return owner_redirect

    form = DeleteForm()
    if not form.validate_on_submit():
        return redirect(url_for("main.settings"))

    if workshop.logo_path:
        delete_upload(workshop.logo_path)
        workshop.logo_path = None
        AuditService.log_action(
            "update",
            "workshop",
            workshop.id,
            "Elimino logo del taller",
            workshop_id=workshop.id,
        )
        db.session.commit()
        flash("Logo eliminado", "success")

    return redirect(url_for("main.settings"))


@main_bp.route("/settings/remove-favicon", methods=["POST"])
@login_required
def settings_remove_favicon():
    workshop, redirect_response = get_workshop_or_redirect()
    if redirect_response:
        return redirect_response

    _, owner_redirect = owner_or_redirect()
    if owner_redirect:
        return owner_redirect

    form = DeleteForm()
    if not form.validate_on_submit():
        return redirect(url_for("main.settings"))

    if workshop.favicon_path:
        delete_upload(workshop.favicon_path)
        workshop.favicon_path = None
        AuditService.log_action(
            "update",
            "workshop",
            workshop.id,
            "Elimino favicon del taller",
            workshop_id=workshop.id,
        )
        db.session.commit()
        flash("Favicon eliminado", "success")

    return redirect(url_for("main.settings"))
