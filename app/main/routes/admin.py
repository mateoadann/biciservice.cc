from datetime import datetime, timezone

from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from sqlalchemy import func
from sqlalchemy.orm import selectinload
from app.main import main_bp
from app.extensions import db
from app.models import (
    AuditLog,
    Bicycle,
    Client,
    Job,
    JobItem,
    JobPart,
    ServiceType,
    Store,
    User,
    Workshop,
    user_workshops,
)
from app.services.audit_service import AuditService
from app.main.forms import DeleteForm, SuperAdminProfileForm
from app.main.helpers import (
    super_admin_or_redirect,
    generate_temp_password
)
from app.auth.utils import send_approval_notification, send_confirmation_email

@main_bp.route("/admin/dashboard")
@login_required
def super_admin_dashboard():
    _, redirect_response = super_admin_or_redirect()
    if redirect_response:
        return redirect_response
    metrics = {
        "owners": User.query.filter_by(role="owner").count(),
        "pending": User.query.filter_by(
            role="owner", is_approved=False, is_active=True
        ).count(),
        "workshops": Workshop.query.count(),
        "stores": Store.query.count(),
        "jobs": Job.query.count(),
    }
    service_revenue = (
        db.session.query(func.coalesce(func.sum(JobItem.unit_price * JobItem.quantity), 0))
        .scalar()
    )
    parts_revenue = (
        db.session.query(func.coalesce(func.sum(JobPart.unit_price * JobPart.quantity), 0))
        .scalar()
    )
    revenue = service_revenue + parts_revenue
    return render_template(
        "main/super_admin/dashboard.html",
        metrics=metrics,
        revenue=revenue,
    )


@main_bp.route("/admin/pending")
@login_required
def super_admin_pending():
    _, redirect_response = super_admin_or_redirect()
    if redirect_response:
        return redirect_response
    owners = (
        User.query.options(selectinload(User.workshops))
        .filter_by(role="owner", is_approved=False, is_active=True)
        .order_by(User.created_at.desc())
        .all()
    )
    form = DeleteForm()
    return render_template("main/super_admin/pending.html", owners=owners, form=form)


@main_bp.route("/admin/pending/<int:user_id>/approve", methods=["POST"])
@login_required
def super_admin_pending_approve(user_id):
    _, redirect_response = super_admin_or_redirect()
    if redirect_response:
        return redirect_response
    form = DeleteForm()
    if not form.validate_on_submit():
        flash("Solicitud invalida", "error")
        return redirect(url_for("main.super_admin_pending"))
    owner = User.query.filter_by(id=user_id, role="owner").first_or_404()
    if not owner.is_active:
        flash("No se puede aprobar un owner inactivo", "error")
        return redirect(url_for("main.super_admin_pending"))
    if owner.is_approved:
        flash("El owner ya fue aprobado", "info")
        return redirect(url_for("main.super_admin_pending"))

    owner.is_approved = True
    owner.approved_at = datetime.now(timezone.utc)
    send_approval_notification(owner)
    AuditService.log_action(
        "update",
        "owner_approval",
        owner.id,
        f"Owner {owner.email} aprobado",
    )
    db.session.commit()
    flash("Owner aprobado", "success")
    return redirect(url_for("main.super_admin_pending"))


@main_bp.route("/admin/pending/<int:user_id>/reject", methods=["POST"])
@login_required
def super_admin_pending_reject(user_id):
    _, redirect_response = super_admin_or_redirect()
    if redirect_response:
        return redirect_response
    form = DeleteForm()
    if not form.validate_on_submit():
        flash("Solicitud invalida", "error")
        return redirect(url_for("main.super_admin_pending"))
    owner = User.query.filter_by(id=user_id, role="owner").first_or_404()
    if owner.is_approved:
        flash("No se puede rechazar un owner aprobado", "error")
        return redirect(url_for("main.super_admin_pending"))
    if not owner.is_active:
        flash("El owner ya esta inactivo", "info")
        return redirect(url_for("main.super_admin_pending"))

    owner.is_active = False
    AuditService.log_action(
        "update",
        "owner_reject",
        owner.id,
        f"Owner {owner.email} rechazado",
    )
    db.session.commit()
    flash("Owner rechazado", "success")
    return redirect(url_for("main.super_admin_pending"))


@main_bp.route("/admin/owners")
@login_required
def super_admin_owners():
    _, redirect_response = super_admin_or_redirect()
    if redirect_response:
        return redirect_response
    owners = (
        User.query.options(selectinload(User.workshops))
        .filter_by(role="owner")
        .order_by(User.created_at.desc())
        .all()
    )
    form = DeleteForm()
    return render_template("main/super_admin/owners.html", owners=owners, form=form)


@main_bp.route("/admin/owners/<int:user_id>/toggle", methods=["POST"])
@login_required
def super_admin_owner_toggle(user_id):
    _, redirect_response = super_admin_or_redirect()
    if redirect_response:
        return redirect_response
    form = DeleteForm()
    if not form.validate_on_submit():
        flash("Solicitud invalida", "error")
        return redirect(url_for("main.super_admin_owners"))
    owner = User.query.filter_by(id=user_id, role="owner").first_or_404()
    owner.is_active = not owner.is_active
    AuditService.log_action(
        "update",
        "owner_status",
        owner.id,
        f"Owner {owner.email} -> {'activo' if owner.is_active else 'inactivo'}",
        workshop_id=owner.workshops[0].id if owner.workshops else None,
    )
    db.session.commit()
    if owner.is_active:
        flash("Owner activado", "success")
    else:
        flash("Owner desactivado", "success")
    return redirect(url_for("main.super_admin_owners"))


@main_bp.route("/admin/owners/<int:user_id>/delete", methods=["POST"])
@login_required
def super_admin_owner_delete(user_id):
    _, redirect_response = super_admin_or_redirect()
    if redirect_response:
        return redirect_response
    form = DeleteForm()
    if not form.validate_on_submit():
        flash("Solicitud invalida", "error")
        return redirect(url_for("main.super_admin_owners"))

    owner = User.query.filter_by(id=user_id, role="owner").first_or_404()
    if owner.is_active or owner.is_approved:
        flash("Solo se pueden eliminar owners rechazados", "error")
        return redirect(url_for("main.super_admin_owners"))
    if len(owner.workshops) > 1:
        flash("No se puede eliminar: owner asociado a multiples talleres", "error")
        return redirect(url_for("main.super_admin_owners"))

    workshop = owner.workshops[0] if owner.workshops else None
    stores = []
    store_ids = []
    if workshop:
        has_business_data = any(
            (
                Client.query.filter_by(workshop_id=workshop.id).first(),
                Bicycle.query.filter_by(workshop_id=workshop.id).first(),
                ServiceType.query.filter_by(workshop_id=workshop.id).first(),
                Job.query.filter_by(workshop_id=workshop.id).first(),
            )
        )
        if has_business_data:
            flash("No se puede eliminar: tiene datos de negocio asociados", "error")
            return redirect(url_for("main.super_admin_owners"))

        other_users = (
            User.query.join(user_workshops)
            .filter(
                user_workshops.c.workshop_id == workshop.id,
                User.id != owner.id,
            )
            .count()
        )
        if other_users:
            flash("No se puede eliminar: el taller tiene otros usuarios", "error")
            return redirect(url_for("main.super_admin_owners"))

        stores = Store.query.filter_by(workshop_id=workshop.id).all()
        store_ids = [store.id for store in stores]

    if store_ids:
        AuditLog.query.filter(AuditLog.store_id.in_(store_ids)).update(
            {AuditLog.store_id: None}, synchronize_session=False
        )
    if workshop:
        AuditLog.query.filter(AuditLog.workshop_id == workshop.id).update(
            {AuditLog.workshop_id: None}, synchronize_session=False
        )
    AuditLog.query.filter(AuditLog.user_id == owner.id).update(
        {AuditLog.user_id: None}, synchronize_session=False
    )

    owner_id = owner.id
    owner_email = owner.email
    owner.store_id = None
    owner.workshops.clear()

    for store in stores:
        db.session.delete(store)
    if workshop:
        db.session.delete(workshop)
    db.session.delete(owner)
    AuditService.log_action(
        "delete",
        "owner",
        owner_id,
        f"Owner {owner_email} eliminado por super admin",
    )
    db.session.commit()
    flash("Owner eliminado con su taller y sucursales", "success")
    return redirect(url_for("main.super_admin_owners"))


@main_bp.route("/admin/owners/<int:user_id>/reset-password", methods=["POST"])
@login_required
def super_admin_owner_reset_password(user_id):
    _, redirect_response = super_admin_or_redirect()
    if redirect_response:
        return redirect_response
    form = DeleteForm()
    if not form.validate_on_submit():
        flash("Solicitud invalida", "error")
        return redirect(url_for("main.super_admin_owners"))
    owner = User.query.filter_by(id=user_id, role="owner").first_or_404()
    temp_password = generate_temp_password()
    owner.set_password(temp_password)
    AuditService.log_action(
        "update",
        "owner_password",
        owner.id,
        f"Reset password owner {owner.email}",
        workshop_id=owner.workshops[0].id if owner.workshops else None,
    )
    db.session.commit()
    flash(f"Contrasena temporal: {temp_password}", "success")
    return redirect(url_for("main.super_admin_owners"))


@main_bp.route("/admin/owners/<int:user_id>/force-confirmation", methods=["POST"])
@login_required
def super_admin_owner_force_confirmation(user_id):
    _, redirect_response = super_admin_or_redirect()
    if redirect_response:
        return redirect_response
    form = DeleteForm()
    if not form.validate_on_submit():
        flash("Solicitud invalida", "error")
        return redirect(url_for("main.super_admin_owners"))
    owner = User.query.filter_by(id=user_id, role="owner").first_or_404()
    owner.email_confirmed = False
    owner.email_confirmed_at = None
    owner.confirmation_sent_at = None
    send_confirmation_email(owner)
    AuditService.log_action(
        "update",
        "owner_email",
        owner.id,
        f"Revalidar email owner {owner.email}",
        workshop_id=owner.workshops[0].id if owner.workshops else None,
    )
    db.session.commit()
    flash("Se envio un nuevo link de confirmacion", "success")
    return redirect(url_for("main.super_admin_owners"))


@main_bp.route("/admin/profile", methods=["GET", "POST"])
@login_required
def super_admin_profile():
    _, redirect_response = super_admin_or_redirect()
    if redirect_response:
        return redirect_response
    form = SuperAdminProfileForm()
    user = current_user
    if request.method == "GET":
        form.full_name.data = user.full_name
        form.email.data = user.email
    if form.validate_on_submit():
        email_value = form.email.data.strip().lower()
        existing = User.query.filter(User.email == email_value, User.id != user.id).first()
        if existing:
            flash("El email ya esta en uso", "error")
            return render_template("main/super_admin/profile.html", form=form)
        user.full_name = form.full_name.data
        user.email = email_value
        if form.password.data:
            user.set_password(form.password.data)
        AuditService.log_action(
            "update",
            "super_admin",
            user.id,
            "Actualizo perfil super admin",
        )
        db.session.commit()
        flash("Perfil actualizado", "success")
        return redirect(url_for("main.super_admin_profile"))
    if request.method == "POST":
        flash("Revisa los datos ingresados", "error")
    return render_template("main/super_admin/profile.html", form=form)


@main_bp.route("/admin/audit")
@login_required
def super_admin_audit():
    _, redirect_response = super_admin_or_redirect()
    if redirect_response:
        return redirect_response
    logs = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(200).all()
    return render_template("main/super_admin/audit.html", logs=logs)
