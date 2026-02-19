from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required
from app.main import main_bp
from app.extensions import db
from app.models import Bicycle, Job
from app.services.client_service import ClientService
from app.services.audit_service import AuditService
from app.main.forms import BicycleForm, DeleteForm
from app.main.helpers import (
    get_workshop_or_redirect,
    paginate_query,
    bicycle_choices,
    client_choices,
    brand_choices,
    resolve_brand
)

@main_bp.route("/bicycles")
@login_required
def bicycles():
    workshop, redirect_response = get_workshop_or_redirect()
    if redirect_response:
        return redirect_response

    page = request.args.get("page", 1, type=int)
    query = Bicycle.query.filter_by(workshop_id=workshop.id).order_by(Bicycle.id.desc())
    pagination = paginate_query(query, page)
    
    table_template_data = {
        "bicycles": pagination["items"],
        "pagination": pagination,
        "delete_form": DeleteForm(),
    }

    if request.args.get("partial"):
        return render_template("main/bicycles/_fragments.html", **table_template_data)

    brand_rows = (
        db.session.query(Bicycle.brand)
        .filter(Bicycle.workshop_id == workshop.id, Bicycle.brand.isnot(None))
        .distinct()
        .order_by(Bicycle.brand.asc())
        .all()
    )
    brands = [row[0] for row in brand_rows]

    return render_template(
        "main/bicycles/index.html",
        **table_template_data,
        brands=brands,
    )


@main_bp.route("/bicycles/<int:bicycle_id>")
@login_required
def bicycles_detail(bicycle_id):
    workshop, redirect_response = get_workshop_or_redirect()
    if redirect_response:
        return redirect_response

    bicycle = (
        Bicycle.query.filter_by(id=bicycle_id, workshop_id=workshop.id).first_or_404()
    )
    created_at, created_by, updated_at, updated_by = AuditService.get_audit_info(
        "bicycle",
        bicycle.id,
        fallback_created_at=bicycle.created_at,
    )
    return render_template(
        "main/bicycles/detail.html",
        bicycle=bicycle,
        created_at=created_at,
        created_by=created_by,
        updated_at=updated_at,
        updated_by=updated_by,
    )


@main_bp.route("/bicycles/new", methods=["GET", "POST"])
@login_required
def bicycles_create():
    workshop, redirect_response = get_workshop_or_redirect()
    if redirect_response:
        return redirect_response

    choices = client_choices(workshop)
    if not choices:
        flash("Primero crea un cliente", "error")
        return redirect(url_for("main.clients_create"))

    form = BicycleForm()
    form.client_id.choices = choices
    form.brand_select.choices = brand_choices()

    if form.validate_on_submit():
        brand = resolve_brand(form)
        ClientService.create_bicycle(
            workshop_id=workshop.id,
            client_id=form.client_id.data,
            brand=brand,
            model=form.model.data,
            description=form.description.data
        )
        flash("Bicicleta creada", "success")
        return redirect(url_for("main.bicycles"))

    if request.method == "POST" and form.errors:
        flash("Revisa los campos ingresados", "error")
        
    client_options = [{"id": cid, "label": label} for cid, label in choices]
    return render_template(
        "main/bicycles/form.html",
        form=form,
        client_options=client_options,
        selected_client_label="",
        title="Nueva bicicleta",
        submit_label="Crear bicicleta",
    )


@main_bp.route("/bicycles/<int:bicycle_id>/edit", methods=["GET", "POST"])
@login_required
def bicycles_edit(bicycle_id):
    workshop, redirect_response = get_workshop_or_redirect()
    if redirect_response:
        return redirect_response

    bicycle = (
        Bicycle.query.filter_by(id=bicycle_id, workshop_id=workshop.id).first_or_404()
    )
    form = BicycleForm()
    choices = client_choices(workshop)
    form.client_id.choices = choices
    form.brand_select.choices = brand_choices()

    if request.method == "GET":
        form.client_id.data = bicycle.client_id
        form.brand_select.data = bicycle.brand or ""
        form.model.data = bicycle.model
        form.description.data = bicycle.description

    if form.validate_on_submit():
        brand = resolve_brand(form)
        ClientService.update_bicycle(
            bicycle,
            client_id=form.client_id.data,
            brand=brand,
            model=form.model.data,
            description=form.description.data
        )
        flash("Bicicleta actualizada", "success")
        return redirect(url_for("main.bicycles"))

    if request.method == "POST" and form.errors:
        flash("Revisa los campos ingresados", "error")
        
    client_options = [{"id": cid, "label": label} for cid, label in choices]
    selected_client_label = ""
    for cid, label in choices:
        if cid == form.client_id.data:
            selected_client_label = label
            break
            
    return render_template(
        "main/bicycles/form.html",
        form=form,
        client_options=client_options,
        selected_client_label=selected_client_label,
        title="Editar bicicleta",
        submit_label="Guardar cambios",
    )


@main_bp.route("/bicycles/<int:bicycle_id>/delete", methods=["POST"])
@login_required
def bicycles_delete(bicycle_id):
    workshop, redirect_response = get_workshop_or_redirect()
    if redirect_response:
        return redirect_response

    form = DeleteForm()
    if not form.validate_on_submit():
        return redirect(url_for("main.bicycles"))

    bicycle = (
        Bicycle.query.filter_by(id=bicycle_id, workshop_id=workshop.id).first_or_404()
    )
    # Note: Job checking logic is not in Service yet. Should I put it in service?
    # Logic: if in_progress, prevent delete.
    # Service layer is cleaner. 
    # But for now I'll replicating the logic here calling db or simple query.
    in_progress = Job.query.filter_by(
        workshop_id=workshop.id, bicycle_id=bicycle.id, status="in_progress"
    ).first()
    if in_progress:
        flash("No puedes eliminar una bicicleta con trabajos en progreso", "error")
        return redirect(url_for("main.bicycles"))

    # Need to handle job deletion cascades. Service handles bicycle deletion logging and delete. 
    # But what about the jobs cleanup? 
    # Original code iterates jobs and deletes them.
    # `ClientService.delete_bicycle` handles only simple delete?
    # I should check `ClientService.delete_bicycle`.
    # It just deletes bicycle. 
    # I need to handle cascade here or update service.
    # I will update service in a separate step or handle here.
    # Handling here for now to avoid switching contexts too much, but ideally should be in service.
    # Wait, `Job` is a dependency.
    # Let's clean up jobs here as per original logic.
    jobs = Job.query.filter_by(
        workshop_id=workshop.id, bicycle_id=bicycle.id
    ).all()
    for job in jobs:
        for part in job.parts:
            db.session.delete(part)
        for item in job.items:
            db.session.delete(item)
        db.session.delete(job)
        
    ClientService.delete_bicycle(bicycle)
    flash("Bicicleta eliminada", "success")
    return redirect(url_for("main.bicycles"))
