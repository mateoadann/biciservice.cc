import os
import re
from pathlib import Path
from uuid import uuid4

from flask import current_app, flash, g, redirect, render_template, request, url_for
from flask_login import login_required
from sqlalchemy import func
from werkzeug.utils import secure_filename
from PIL import Image
from io import BytesIO

from . import main_bp
from ..extensions import db
from ..models import Bicycle, Client, Job, JobItem, ServiceType
from .forms import (
    BRAND_CHOICES,
    BicycleForm,
    ClientForm,
    DeleteForm,
    JobForm,
    JobStatusForm,
    ServiceTypeForm,
    WorkshopSettingsForm,
)


def _validate_upload(file_storage):
    filename = secure_filename(file_storage.filename)
    if not filename or "." not in filename:
        return None, "Nombre de archivo invalido."
    ext = filename.rsplit(".", 1)[-1].lower()
    allowed = current_app.config["ALLOWED_IMAGE_EXTENSIONS"]
    if ext not in allowed:
        return None, "Formato de archivo no permitido."
    data = file_storage.read()
    file_storage.stream.seek(0)
    if ext == "svg":
        text = data.decode("utf-8", errors="ignore").lower()
        if "<svg" not in text or re.search(r"<script|onload=|onerror=", text):
            return None, "SVG invalido."
    else:
        try:
            image = Image.open(BytesIO(data))
            image.verify()
            if image.format not in {"JPEG", "PNG", "ICO"}:
                return None, "Archivo de imagen invalido."
        except Exception:
            return None, "Archivo de imagen invalido."
    return filename, None


def _save_upload(file_storage, workshop_id):
    if not file_storage:
        return None, None
    filename, error = _validate_upload(file_storage)
    if error:
        return None, error
    upload_root = Path(current_app.config["UPLOAD_FOLDER"]) / str(workshop_id)
    upload_root.mkdir(parents=True, exist_ok=True)
    unique_name = f"{uuid4().hex}_{filename}"
    file_path = upload_root / unique_name
    file_storage.save(file_path)
    rel_path = os.path.relpath(file_path, Path(__file__).resolve().parent.parent / "static")
    return rel_path.replace(os.path.sep, "/"), None


def _delete_upload(rel_path):
    if not rel_path:
        return
    file_path = Path(current_app.static_folder) / rel_path
    if file_path.exists():
        file_path.unlink()


def _get_workshop_or_redirect():
    workshop = g.active_workshop
    if workshop is None:
        flash("No hay taller seleccionado", "error")
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
    services = _services_list(workshop)
    return [(service.id, service.name) for service in services]


def _services_list(workshop):
    return (
        ServiceType.query.filter_by(workshop_id=workshop.id)
        .order_by(ServiceType.name.asc())
        .all()
    )


def _brand_choices():
    return [("", "Seleccionar marca")] + [(brand, brand) for brand in BRAND_CHOICES]


def _resolve_brand(form):
    return form.brand_select.data or None


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
    agenda_jobs = []
    summary = {
        "revenue": 0,
        "open": 0,
        "in_progress": 0,
        "ready": 0,
        "closed": 0,
        "services_active": 0,
    }
    if workshop:
        agenda_jobs = (
            Job.query.filter_by(workshop_id=workshop.id)
            .order_by(Job.created_at.desc())
            .limit(5)
            .all()
        )
        revenue = (
            db.session.query(
                func.coalesce(func.sum(JobItem.unit_price * JobItem.quantity), 0)
            )
            .join(Job, Job.id == JobItem.job_id)
            .filter(Job.workshop_id == workshop.id)
            .scalar()
        )
        status_counts = dict(
            db.session.query(Job.status, func.count(Job.id))
            .filter(Job.workshop_id == workshop.id)
            .group_by(Job.status)
            .all()
        )
        summary = {
            "revenue": revenue,
            "open": status_counts.get("open", 0),
            "in_progress": status_counts.get("in_progress", 0),
            "ready": status_counts.get("ready", 0),
            "closed": status_counts.get("closed", 0),
            "services_active": ServiceType.query.filter_by(
                workshop_id=workshop.id, is_active=True
            ).count(),
        }

    return render_template(
        "main/dashboard.html",
        counts=counts,
        workshop=workshop,
        agenda_jobs=agenda_jobs,
        summary=summary,
    )


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

        logo_path, logo_error = _save_upload(form.logo.data, workshop.id)
        if logo_error:
            flash(logo_error, "error")
            return redirect(url_for("main.settings"))
        if logo_path:
            if workshop.logo_path and workshop.logo_path != logo_path:
                _delete_upload(workshop.logo_path)
            workshop.logo_path = logo_path

        favicon_path, favicon_error = _save_upload(form.favicon.data, workshop.id)
        if favicon_error:
            flash(favicon_error, "error")
            return redirect(url_for("main.settings"))
        if favicon_path:
            if workshop.favicon_path and workshop.favicon_path != favicon_path:
                _delete_upload(workshop.favicon_path)
            workshop.favicon_path = favicon_path

        db.session.commit()
        flash("Configuracion del taller actualizada", "success")
        return redirect(url_for("main.settings"))

    if request.method == "POST":
        flash("Revisa los campos ingresados", "error")
    return render_template("main/settings.html", form=form, workshop=workshop)


@main_bp.route("/settings/remove-logo", methods=["POST"])
@login_required
def settings_remove_logo():
    workshop, redirect_response = _get_workshop_or_redirect()
    if redirect_response:
        return redirect_response

    form = DeleteForm()
    if not form.validate_on_submit():
        return redirect(url_for("main.settings"))

    if workshop.logo_path:
        _delete_upload(workshop.logo_path)
        workshop.logo_path = None
        db.session.commit()
        flash("Logo eliminado", "success")

    return redirect(url_for("main.settings"))


@main_bp.route("/settings/remove-favicon", methods=["POST"])
@login_required
def settings_remove_favicon():
    workshop, redirect_response = _get_workshop_or_redirect()
    if redirect_response:
        return redirect_response

    form = DeleteForm()
    if not form.validate_on_submit():
        return redirect(url_for("main.settings"))

    if workshop.favicon_path:
        _delete_upload(workshop.favicon_path)
        workshop.favicon_path = None
        db.session.commit()
        flash("Favicon eliminado", "success")

    return redirect(url_for("main.settings"))


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

    if request.method == "POST":
        flash("Revisa los campos ingresados", "error")
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

    if request.method == "POST":
        flash("Revisa los campos ingresados", "error")
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
    brands = sorted({bicycle.brand for bicycle in bicycles_list if bicycle.brand})
    return render_template(
        "main/bicycles/index.html",
        bicycles=bicycles_list,
        brands=brands,
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
    form.brand_select.choices = _brand_choices()

    if form.validate_on_submit():
        brand = _resolve_brand(form)
        bicycle = Bicycle(
            workshop_id=workshop.id,
            client_id=form.client_id.data,
            brand=brand,
            model=form.model.data,
            description=form.description.data,
        )
        db.session.add(bicycle)
        db.session.commit()
        flash("Bicicleta creada", "success")
        return redirect(url_for("main.bicycles"))

    if request.method == "POST":
        flash("Revisa los campos ingresados", "error")
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
    form.brand_select.choices = _brand_choices()

    if request.method == "GET":
        form.client_id.data = bicycle.client_id
        form.brand_select.data = bicycle.brand or ""
        form.model.data = bicycle.model
        form.description.data = bicycle.description

    if form.validate_on_submit():
        brand = _resolve_brand(form)
        bicycle.client_id = form.client_id.data
        bicycle.brand = brand
        bicycle.model = form.model.data
        bicycle.description = form.description.data
        db.session.commit()
        flash("Bicicleta actualizada", "success")
        return redirect(url_for("main.bicycles"))

    if request.method == "POST":
        flash("Revisa los campos ingresados", "error")
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
    in_progress = Job.query.filter_by(
        workshop_id=workshop.id, bicycle_id=bicycle.id, status="in_progress"
    ).first()
    if in_progress:
        flash("No puedes eliminar una bicicleta con trabajos en progreso", "error")
        return redirect(url_for("main.bicycles"))

    jobs = Job.query.filter_by(
        workshop_id=workshop.id, bicycle_id=bicycle.id
    ).all()
    for job in jobs:
        for item in job.items:
            db.session.delete(item)
        db.session.delete(job)

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

    if request.method == "POST":
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
    workshop, redirect_response = _get_workshop_or_redirect()
    if redirect_response:
        return redirect_response

    service = (
        ServiceType.query.filter_by(id=service_id, workshop_id=workshop.id).first_or_404()
    )
    form = ServiceTypeForm(obj=service)

    if form.validate_on_submit():
        service.name = form.name.data
        service.description = form.description.data
        if form.base_price.data is not None:
            service.base_price = form.base_price.data
        service.is_active = form.is_active.data
        db.session.commit()
        flash("Service actualizado", "success")
        return redirect(url_for("main.services"))

    if request.method == "POST":
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
        status_form=JobStatusForm(),
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
    services_list = _services_list(workshop)
    form.service_type_ids.choices = [(service.id, service.name) for service in services_list]

    if form.validate_on_submit():
        job = Job(
            workshop_id=workshop.id,
            bicycle_id=form.bicycle_id.data,
            status=form.status.data,
            notes=form.notes.data,
        )
        db.session.add(job)
        db.session.flush()

        selected_ids = {
            service_id for service_id in form.service_type_ids.data if service_id
        }
        if selected_ids:
            services = (
                ServiceType.query.filter(
                    ServiceType.workshop_id == workshop.id,
                    ServiceType.id.in_(selected_ids),
                ).all()
            )
            for service in services:
                job_item = JobItem(
                    job_id=job.id,
                    service_type_id=service.id,
                    quantity=1,
                    unit_price=service.base_price,
                )
                db.session.add(job_item)

        db.session.commit()
        flash("Trabajo creado", "success")
        return redirect(url_for("main.jobs"))

    if request.method == "POST":
        flash("Revisa los campos ingresados", "error")
    selected_ids = set(form.service_type_ids.data or [])
    return render_template(
        "main/jobs/form.html",
        form=form,
        services=services_list,
        selected_ids=selected_ids,
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
    services_list = _services_list(workshop)
    form.service_type_ids.choices = [(service.id, service.name) for service in services_list]
    existing_items = {item.service_type_id: item for item in job.items}

    if request.method == "GET":
        form.bicycle_id.data = job.bicycle_id
        form.status.data = job.status
        form.notes.data = job.notes
        form.service_type_ids.data = list(existing_items.keys())

    if form.validate_on_submit():
        job.bicycle_id = form.bicycle_id.data
        job.status = form.status.data
        job.notes = form.notes.data

        selected_ids = {
            service_id for service_id in form.service_type_ids.data if service_id
        }
        services = (
            ServiceType.query.filter(
                ServiceType.workshop_id == workshop.id,
                ServiceType.id.in_(selected_ids),
            ).all()
        )
        selected_map = {service.id: service for service in services}

        for service_id, item in existing_items.items():
            if service_id not in selected_ids:
                db.session.delete(item)

        for service_id, service in selected_map.items():
            if service_id not in existing_items:
                db.session.add(
                    JobItem(
                        job_id=job.id,
                        service_type_id=service_id,
                        quantity=1,
                        unit_price=service.base_price,
                    )
                )

        db.session.commit()
        flash("Trabajo actualizado", "success")
        return redirect(url_for("main.jobs"))

    if request.method == "POST":
        flash("Revisa los campos ingresados", "error")
    selected_ids = set(form.service_type_ids.data or [])
    return render_template(
        "main/jobs/form.html",
        form=form,
        services=services_list,
        selected_ids=selected_ids,
        title="Editar trabajo",
        submit_label="Guardar cambios",
    )


@main_bp.route("/jobs/<int:job_id>/status", methods=["POST"])
@login_required
def jobs_status(job_id):
    workshop, redirect_response = _get_workshop_or_redirect()
    if redirect_response:
        return redirect_response

    form = JobStatusForm()
    if not form.validate_on_submit():
        return redirect(url_for("main.jobs"))

    job = Job.query.filter_by(id=job_id, workshop_id=workshop.id).first_or_404()
    job.status = form.status.data
    db.session.commit()
    flash("Estado actualizado correctamente", "success")
    return redirect(url_for("main.jobs"))


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
    if job.status == "in_progress":
        flash("No puedes eliminar un trabajo en proceso", "error")
        return redirect(url_for("main.jobs"))
    for item in job.items:
        db.session.delete(item)
    db.session.delete(job)
    db.session.commit()
    flash("Trabajo eliminado", "success")
    return redirect(url_for("main.jobs"))
