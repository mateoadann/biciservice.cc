from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required
from app.main import main_bp
from app.models import ServiceType
from app.services.inventory_service import InventoryService
from app.services.audit_service import AuditService
from app.main.forms import ServiceTypeForm, DeleteForm
from app.main.helpers import get_workshop_or_redirect

@main_bp.route("/services")
@login_required
def services():
    workshop, redirect_response = get_workshop_or_redirect()
    if redirect_response:
        return redirect_response

    services_list = (
        ServiceType.query.filter_by(workshop_id=workshop.id)
        .order_by(ServiceType.name.asc())
        .all()
    )
    return render_template(
        "main/services/index.html",
        services=services_list,
        delete_form=DeleteForm(),
    )


@main_bp.route("/services/<int:service_id>")
@login_required
def services_detail(service_id):
    workshop, redirect_response = get_workshop_or_redirect()
    if redirect_response:
        return redirect_response

    service = (
        ServiceType.query.filter_by(id=service_id, workshop_id=workshop.id).first_or_404()
    )
    created_at, created_by, updated_at, updated_by = AuditService.get_audit_info(
        "service",
        service.id,
        fallback_created_at=service.created_at,
    )
    return render_template(
        "main/services/detail.html",
        service=service,
        created_at=created_at,
        created_by=created_by,
        updated_at=updated_at,
        updated_by=updated_by,
    )


@main_bp.route("/services/new", methods=["GET", "POST"])
@login_required
def services_create():
    workshop, redirect_response = get_workshop_or_redirect()
    if redirect_response:
        return redirect_response

    form = ServiceTypeForm()
    if request.method == "GET":
        form.is_active.data = True

    if form.validate_on_submit():
        InventoryService.create_service(
            workshop_id=workshop.id,
            name=form.name.data,
            description=form.description.data,
            base_price=form.base_price.data,
            is_active=form.is_active.data
        )
        flash("Service creado", "success")
        return redirect(url_for("main.services"))

    if request.method == "POST" and form.errors:
        flash("Revisa los campos ingresados", "error")
    return render_template(
        "main/services/form.html",
        form=form,
        title="Nuevo service",
        submit_label="Crear service",
        initial_base_price=None,
    )


@main_bp.route("/services/<int:service_id>/edit", methods=["GET", "POST"])
@login_required
def services_edit(service_id):
    workshop, redirect_response = get_workshop_or_redirect()
    if redirect_response:
        return redirect_response

    service = (
        ServiceType.query.filter_by(id=service_id, workshop_id=workshop.id).first_or_404()
    )
    form = ServiceTypeForm(obj=service)

    if form.validate_on_submit():
        InventoryService.update_service(
            service,
            name=form.name.data,
            description=form.description.data,
            base_price=form.base_price.data,
            is_active=form.is_active.data
        )
        flash("Service actualizado", "success")
        return redirect(url_for("main.services"))

    if request.method == "POST" and form.errors:
        flash("Revisa los campos ingresados", "error")
    return render_template(
        "main/services/form.html",
        form=form,
        title="Editar service",
        submit_label="Guardar cambios",
        initial_base_price=service.base_price,
    )


@main_bp.route("/services/<int:service_id>/delete", methods=["POST"])
@login_required
def services_delete(service_id):
    workshop, redirect_response = get_workshop_or_redirect()
    if redirect_response:
        return redirect_response

    form = DeleteForm()
    if not form.validate_on_submit():
        return redirect(url_for("main.services"))

    service = (
        ServiceType.query.filter_by(id=service_id, workshop_id=workshop.id).first_or_404()
    )
    if service.job_items:
        flash("No se puede borrar un service asociado a trabajos", "error")
        return redirect(url_for("main.services"))

    InventoryService.delete_service(service)
    flash("Service eliminado", "success")
    return redirect(url_for("main.services"))
