import os
from pathlib import Path

from flask import current_app, flash, g, redirect, render_template, request, url_for
from flask_login import login_required
from werkzeug.utils import secure_filename

from . import main_bp
from ..extensions import db
from ..models import Bicycle, Client, Job, JobItem, ServiceType
from .forms import (
    BicycleForm,
    ClientForm,
    DeleteForm,
    JobForm,
    ServiceTypeForm,
    WorkshopSettingsForm,
)


def _save_upload(file_storage, workshop_id):
    if not file_storage:
        return None
    filename = secure_filename(file_storage.filename)
    if not filename:
        return None
    upload_root = Path(current_app.config["UPLOAD_FOLDER"]) / str(workshop_id)
    upload_root.mkdir(parents=True, exist_ok=True)
    file_path = upload_root / filename
    file_storage.save(file_path)
    rel_path = os.path.relpath(file_path, Path(__file__).resolve().parent.parent / "static")
    return rel_path.replace(os.path.sep, "/")


def _get_workshop_or_redirect():
    workshop = g.active_workshop
    if workshop is None:
        flash("No workshop selected", "error")
        return None, redirect(url_for("main.dashboard"))
    return workshop, None


def _client_choices(workshop):
    clients = (
        Client.query.filter_by(workshop_id=workshop.id)
        .order_by(Client.full_name.asc())
        .all()
    )
    return [(client.id, client.full_name) for client in clients]


def _bicycle_choices(workshop):
    bicycles = (
        Bicycle.query.filter_by(workshop_id=workshop.id)
        .order_by(Bicycle.id.desc())
        .all()
    )
    choices = []
    for bicycle in bicycles:
        label_parts = [bicycle.brand, bicycle.model]
        label = " ".join(part for part in label_parts if part)
        if not label:
            label = "Bicicleta"
        choices.append((bicycle.id, f"{label} - {bicycle.client.full_name}"))
    return choices


def _service_choices(workshop):
    services = (
        ServiceType.query.filter_by(workshop_id=workshop.id)
        .order_by(ServiceType.name.asc())
        .all()
    )
    choices = [(0, "Sin service")]
    for service in services:
        price_label = f"{service.base_price:.2f}" if service.base_price else "0.00"
        choices.append((service.id, f"{service.name} (${price_label})"))
    return choices


@main_bp.route("/")
def index():
    return redirect(url_for("main.dashboard"))


@main_bp.route("/dashboard")
@login_required
def dashboard():
    workshop = g.active_workshop
    counts = {
        "clients": Client.query.filter_by(workshop_id=workshop.id).count()
        if workshop
        else 0,
        "bicycles": Bicycle.query.filter_by(workshop_id=workshop.id).count()
        if workshop
        else 0,
        "services": ServiceType.query.filter_by(workshop_id=workshop.id).count()
        if workshop
        else 0,
        "jobs": Job.query.filter_by(workshop_id=workshop.id).count() if workshop else 0,
    }
    return render_template("main/dashboard.html", counts=counts, workshop=workshop)


@main_bp.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    workshop, redirect_response = _get_workshop_or_redirect()
    if redirect_response:
        return redirect_response

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

        logo_path = _save_upload(form.logo.data, workshop.id)
        if logo_path:
            workshop.logo_path = logo_path
        favicon_path = _save_upload(form.favicon.data, workshop.id)
        if favicon_path:
            workshop.favicon_path = favicon_path

        db.session.commit()
        flash("Workshop settings updated", "success")
        return redirect(url_for("main.settings"))

    return render_template("main/settings.html", form=form, workshop=workshop)


@main_bp.route("/clients")
@login_required
def clients():
    workshop, redirect_response = _get_workshop_or_redirect()
    if redirect_response:
        return redirect_response
    clients_list = (
        Client.query.filter_by(workshop_id=workshop.id)
        .order_by(Client.full_name.asc())
        .all()
    )
    return render_template(
        "main/clients/index.html",
        clients=clients_list,
        delete_form=DeleteForm(),
    )


@main_bp.route("/clients/new", methods=["GET", "POST"])
@login_required
def clients_create():
    workshop, redirect_response = _get_workshop_or_redirect()
    if redirect_response:
        return redirect_response

    form = ClientForm()
    if form.validate_on_submit():
        client = Client(
            workshop_id=workshop.id,
            full_name=form.full_name.data,
            email=form.email.data,
            phone=form.phone.data,
        )
        db.session.add(client)
        db.session.commit()
        flash("Cliente creado", "success")
        return redirect(url_for("main.clients"))

    return render_template(
        "main/clients/form.html",
        form=form,
        title="Nuevo cliente",
        submit_label="Crear cliente",
    )


@main_bp.route("/clients/<int:client_id>/edit", methods=["GET", "POST"])
@login_required
def clients_edit(client_id):
    workshop, redirect_response = _get_workshop_or_redirect()
    if redirect_response:
        return redirect_response

    client = Client.query.filter_by(id=client_id, workshop_id=workshop.id).first_or_404()
    form = ClientForm()

    if request.method == "GET":
        form.full_name.data = client.full_name
        form.email.data = client.email
        form.phone.data = client.phone

    if form.validate_on_submit():
        client.full_name = form.full_name.data
        client.email = form.email.data
        client.phone = form.phone.data
        db.session.commit()
        flash("Cliente actualizado", "success")
        return redirect(url_for("main.clients"))

    return render_template(
        "main/clients/form.html",
        form=form,
        title="Editar cliente",
        submit_label="Guardar cambios",
    )


@main_bp.route("/clients/<int:client_id>/delete", methods=["POST"])
@login_required
def clients_delete(client_id):
    workshop, redirect_response = _get_workshop_or_redirect()
    if redirect_response:
        return redirect_response

    form = DeleteForm()
    if not form.validate_on_submit():
        return redirect(url_for("main.clients"))

    client = Client.query.filter_by(id=client_id, workshop_id=workshop.id).first_or_404()
    if client.bicycles:
        flash("No se puede borrar un cliente con bicicletas", "error")
        return redirect(url_for("main.clients"))

    db.session.delete(client)
    db.session.commit()
    flash("Cliente eliminado", "success")
    return redirect(url_for("main.clients"))


@main_bp.route("/bicycles")
@login_required
def bicycles():
    workshop, redirect_response = _get_workshop_or_redirect()
    if redirect_response:
        return redirect_response

    bicycles_list = (
        Bicycle.query.filter_by(workshop_id=workshop.id)
        .order_by(Bicycle.id.desc())
        .all()
    )
    return render_template(
        "main/bicycles/index.html",
        bicycles=bicycles_list,
        delete_form=DeleteForm(),
    )


@main_bp.route("/bicycles/new", methods=["GET", "POST"])
@login_required
def bicycles_create():
    workshop, redirect_response = _get_workshop_or_redirect()
    if redirect_response:
        return redirect_response

    client_choices = _client_choices(workshop)
    if not client_choices:
        flash("Primero crea un cliente", "error")
        return redirect(url_for("main.clients_create"))

    form = BicycleForm()
    form.client_id.choices = client_choices

    if form.validate_on_submit():
        bicycle = Bicycle(
            workshop_id=workshop.id,
            client_id=form.client_id.data,
            brand=form.brand.data,
            model=form.model.data,
            serial_number=form.serial_number.data,
        )
        db.session.add(bicycle)
        db.session.commit()
        flash("Bicicleta creada", "success")
        return redirect(url_for("main.bicycles"))

    return render_template(
        "main/bicycles/form.html",
        form=form,
        title="Nueva bicicleta",
        submit_label="Crear bicicleta",
    )


@main_bp.route("/bicycles/<int:bicycle_id>/edit", methods=["GET", "POST"])
@login_required
def bicycles_edit(bicycle_id):
    workshop, redirect_response = _get_workshop_or_redirect()
    if redirect_response:
        return redirect_response

    bicycle = (
        Bicycle.query.filter_by(id=bicycle_id, workshop_id=workshop.id).first_or_404()
    )
    form = BicycleForm()
    form.client_id.choices = _client_choices(workshop)

    if request.method == "GET":
        form.client_id.data = bicycle.client_id
        form.brand.data = bicycle.brand
        form.model.data = bicycle.model
        form.serial_number.data = bicycle.serial_number

    if form.validate_on_submit():
        bicycle.client_id = form.client_id.data
        bicycle.brand = form.brand.data
        bicycle.model = form.model.data
        bicycle.serial_number = form.serial_number.data
        db.session.commit()
        flash("Bicicleta actualizada", "success")
        return redirect(url_for("main.bicycles"))

    return render_template(
        "main/bicycles/form.html",
        form=form,
        title="Editar bicicleta",
        submit_label="Guardar cambios",
    )


@main_bp.route("/bicycles/<int:bicycle_id>/delete", methods=["POST"])
@login_required
def bicycles_delete(bicycle_id):
    workshop, redirect_response = _get_workshop_or_redirect()
    if redirect_response:
        return redirect_response

    form = DeleteForm()
    if not form.validate_on_submit():
        return redirect(url_for("main.bicycles"))

    bicycle = (
        Bicycle.query.filter_by(id=bicycle_id, workshop_id=workshop.id).first_or_404()
    )
    if bicycle.jobs:
        flash("No se puede borrar una bicicleta con trabajos", "error")
        return redirect(url_for("main.bicycles"))

    db.session.delete(bicycle)
    db.session.commit()
    flash("Bicicleta eliminada", "success")
    return redirect(url_for("main.bicycles"))


@main_bp.route("/services")
@login_required
def services():
    workshop, redirect_response = _get_workshop_or_redirect()
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


@main_bp.route("/services/new", methods=["GET", "POST"])
@login_required
def services_create():
    workshop, redirect_response = _get_workshop_or_redirect()
    if redirect_response:
        return redirect_response

    form = ServiceTypeForm()
    if request.method == "GET":
        form.is_active.data = True

    if form.validate_on_submit():
        service = ServiceType(
            workshop_id=workshop.id,
            name=form.name.data,
            description=form.description.data,
            base_price=form.base_price.data or 0,
            is_active=form.is_active.data,
        )
        db.session.add(service)
        db.session.commit()
        flash("Service creado", "success")
        return redirect(url_for("main.services"))

    return render_template(
        "main/services/form.html",
        form=form,
        title="Nuevo service",
        submit_label="Crear service",
    )


@main_bp.route("/services/<int:service_id>/edit", methods=["GET", "POST"])
@login_required
def services_edit(service_id):
    workshop, redirect_response = _get_workshop_or_redirect()
    if redirect_response:
        return redirect_response

    service = (
        ServiceType.query.filter_by(id=service_id, workshop_id=workshop.id).first_or_404()
    )
    form = ServiceTypeForm()

    if request.method == "GET":
        form.name.data = service.name
        form.description.data = service.description
        form.base_price.data = service.base_price
        form.is_active.data = service.is_active

    if form.validate_on_submit():
        service.name = form.name.data
        service.description = form.description.data
        service.base_price = form.base_price.data or 0
        service.is_active = form.is_active.data
        db.session.commit()
        flash("Service actualizado", "success")
        return redirect(url_for("main.services"))

    return render_template(
        "main/services/form.html",
        form=form,
        title="Editar service",
        submit_label="Guardar cambios",
    )


@main_bp.route("/services/<int:service_id>/delete", methods=["POST"])
@login_required
def services_delete(service_id):
    workshop, redirect_response = _get_workshop_or_redirect()
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

    db.session.delete(service)
    db.session.commit()
    flash("Service eliminado", "success")
    return redirect(url_for("main.services"))


@main_bp.route("/jobs")
@login_required
def jobs():
    workshop, redirect_response = _get_workshop_or_redirect()
    if redirect_response:
        return redirect_response

    jobs_list = (
        Job.query.filter_by(workshop_id=workshop.id)
        .order_by(Job.created_at.desc())
        .all()
    )
    return render_template(
        "main/jobs/index.html",
        jobs=jobs_list,
        delete_form=DeleteForm(),
    )


@main_bp.route("/jobs/new", methods=["GET", "POST"])
@login_required
def jobs_create():
    workshop, redirect_response = _get_workshop_or_redirect()
    if redirect_response:
        return redirect_response

    bicycle_choices = _bicycle_choices(workshop)
    if not bicycle_choices:
        flash("Primero crea una bicicleta", "error")
        return redirect(url_for("main.bicycles_create"))

    form = JobForm()
    form.bicycle_id.choices = bicycle_choices
    form.service_type_id.choices = _service_choices(workshop)

    if form.validate_on_submit():
        job = Job(
            workshop_id=workshop.id,
            bicycle_id=form.bicycle_id.data,
            status=form.status.data,
            notes=form.notes.data,
        )
        db.session.add(job)
        db.session.flush()

        service_type_id = form.service_type_id.data
        if service_type_id:
            service = ServiceType.query.filter_by(
                id=service_type_id, workshop_id=workshop.id
            ).first()
            if service:
                unit_price = (
                    form.unit_price.data
                    if form.unit_price.data is not None
                    else service.base_price
                )
                quantity = form.quantity.data or 1
                job_item = JobItem(
                    job_id=job.id,
                    service_type_id=service.id,
                    quantity=quantity,
                    unit_price=unit_price,
                )
                db.session.add(job_item)

        db.session.commit()
        flash("Trabajo creado", "success")
        return redirect(url_for("main.jobs"))

    return render_template(
        "main/jobs/form.html",
        form=form,
        title="Nuevo trabajo",
        submit_label="Crear trabajo",
    )


@main_bp.route("/jobs/<int:job_id>/edit", methods=["GET", "POST"])
@login_required
def jobs_edit(job_id):
    workshop, redirect_response = _get_workshop_or_redirect()
    if redirect_response:
        return redirect_response

    job = Job.query.filter_by(id=job_id, workshop_id=workshop.id).first_or_404()
    form = JobForm()
    form.bicycle_id.choices = _bicycle_choices(workshop)
    form.service_type_id.choices = _service_choices(workshop)

    job_item = job.items[0] if job.items else None

    if request.method == "GET":
        form.bicycle_id.data = job.bicycle_id
        form.status.data = job.status
        form.notes.data = job.notes
        if job_item:
            form.service_type_id.data = job_item.service_type_id
            form.quantity.data = job_item.quantity
            form.unit_price.data = job_item.unit_price
        else:
            form.service_type_id.data = 0

    if form.validate_on_submit():
        job.bicycle_id = form.bicycle_id.data
        job.status = form.status.data
        job.notes = form.notes.data

        service_type_id = form.service_type_id.data
        if service_type_id:
            service = ServiceType.query.filter_by(
                id=service_type_id, workshop_id=workshop.id
            ).first()
            if service:
                unit_price = (
                    form.unit_price.data
                    if form.unit_price.data is not None
                    else service.base_price
                )
                quantity = form.quantity.data or 1
                if job_item:
                    job_item.service_type_id = service.id
                    job_item.unit_price = unit_price
                    job_item.quantity = quantity
                else:
                    job_item = JobItem(
                        job_id=job.id,
                        service_type_id=service.id,
                        quantity=quantity,
                        unit_price=unit_price,
                    )
                    db.session.add(job_item)
        elif job_item:
            db.session.delete(job_item)

        db.session.commit()
        flash("Trabajo actualizado", "success")
        return redirect(url_for("main.jobs"))

    return render_template(
        "main/jobs/form.html",
        form=form,
        title="Editar trabajo",
        submit_label="Guardar cambios",
    )


@main_bp.route("/jobs/<int:job_id>/delete", methods=["POST"])
@login_required
def jobs_delete(job_id):
    workshop, redirect_response = _get_workshop_or_redirect()
    if redirect_response:
        return redirect_response

    form = DeleteForm()
    if not form.validate_on_submit():
        return redirect(url_for("main.jobs"))

    job = Job.query.filter_by(id=job_id, workshop_id=workshop.id).first_or_404()
    for item in job.items:
        db.session.delete(item)
    db.session.delete(job)
    db.session.commit()
    flash("Trabajo eliminado", "success")
    return redirect(url_for("main.jobs"))
