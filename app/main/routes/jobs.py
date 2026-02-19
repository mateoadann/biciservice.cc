from datetime import date

from flask import render_template, request, redirect, url_for, flash, g, send_file
from flask_login import login_required, current_user
from sqlalchemy.orm import joinedload

from app.main import main_bp
from app.extensions import db
from app.models import Bicycle, Job, JobItem
from app.services.job_service import JobService
from app.services.audit_service import AuditService
from app.services.pdf_service import generate_job_pdf, build_pdf_filename
from app.main.forms import JobForm, JobStatusForm, DeleteForm
from app.main.helpers import (
    build_job_whatsapp_message,
    get_workshop_or_redirect,
    get_store_or_redirect,
    paginate_query,
    format_currency,
    normalize_whatsapp_phone,
    bicycle_choices,
    services_list,
    brand_choices,
)

@main_bp.route("/jobs")
@login_required
def jobs():
    workshop, redirect_response = get_workshop_or_redirect()
    if redirect_response:
        return redirect_response

    store, store_redirect = get_store_or_redirect()
    if store_redirect:
        return store_redirect

    page = request.args.get("page", 1, type=int)
    requested_status = (request.args.get("status") or "all").strip().lower()
    allowed_statuses = {
        "all",
        "open",
        "in_progress",
        "ready",
        "closed",
        "cancelled",
        "overdue",
    }
    active_status = requested_status if requested_status in allowed_statuses else "all"

    query = Job.query.filter_by(workshop_id=workshop.id, store_id=store.id)
    if active_status == "overdue":
        query = query.filter(
            Job.status.in_(["open", "in_progress", "ready"]),
            Job.estimated_delivery_at < date.today(),
        )
    elif active_status != "all":
        query = query.filter(Job.status == active_status)

    query = query.order_by(Job.created_at.desc())
    pagination = paginate_query(query, page)

    table_template_data = {
        "jobs": pagination["items"],
        "pagination": pagination,
        "delete_form": DeleteForm(),
        "status_form": JobStatusForm(),
        "active_status": active_status,
    }

    if request.args.get("partial"):
        return render_template("main/jobs/_fragments.html", **table_template_data)

    return render_template(
        "main/jobs/index.html",
        **table_template_data,
    )


@main_bp.route("/jobs/<int:job_id>")
@login_required
def jobs_detail(job_id):
    workshop, redirect_response = get_workshop_or_redirect()
    if redirect_response:
        return redirect_response

    store, store_redirect = get_store_or_redirect()
    if store_redirect:
        return store_redirect

    job = (
        Job.query.filter_by(id=job_id, workshop_id=workshop.id, store_id=store.id)
        .options(
            joinedload(Job.bicycle).joinedload(Bicycle.client),
            joinedload(Job.items).joinedload(JobItem.service_type),
            joinedload(Job.parts),
        )
        .first_or_404()
    )
    
    created_at, created_by, updated_at, updated_by = AuditService.get_audit_info(
        "job",
        job.id,
        fallback_created_at=job.created_at,
    )
    service_total = sum(
        (item.unit_price or 0) * (item.quantity or 0) for item in job.items
    )
    parts_total = sum(
        (part.unit_price or 0) * (part.quantity or 0) for part in job.parts
    )
    total = service_total + parts_total
    client_phone = ""
    if job.bicycle and job.bicycle.client and job.bicycle.client.phone:
        client_phone = job.bicycle.client.phone
    whatsapp_phone = normalize_whatsapp_phone(client_phone)
    whatsapp_message = build_job_whatsapp_message(workshop, job, total)

    return render_template(
        "main/jobs/detail.html",
        job=job,
        created_at=created_at,
        created_by=created_by,
        updated_at=updated_at,
        updated_by=updated_by,
        service_total=service_total,
        parts_total=parts_total,
        total=total,
        whatsapp_phone=whatsapp_phone,
        whatsapp_message=whatsapp_message,
    )


@main_bp.route("/jobs/new", methods=["GET", "POST"])
@login_required
def jobs_create():
    workshop, redirect_response = get_workshop_or_redirect()
    if redirect_response:
        return redirect_response

    store, store_redirect = get_store_or_redirect()
    if store_redirect:
        return store_redirect

    choices = bicycle_choices(workshop)
    if not choices:
        flash("Primero crea una bicicleta", "error")
        return redirect(url_for("main.bicycles_create"))

    form = JobForm()
    form.bicycle_id.choices = choices
    services = services_list(workshop)
    form.service_type_ids.choices = [(service.id, service.name) for service in services]

    if form.validate_on_submit():
        parts, part_error = JobService.parse_job_parts(request.form)
        if part_error:
            flash(part_error, "error")
        else:
            service_prices = {}
            for sid in (form.service_type_ids.data or []):
                raw = request.form.get(f"service_price_{sid}", "")
                parsed = JobService.parse_decimal(raw)
                if parsed is not None:
                    service_prices[sid] = parsed
            JobService.create_job(
                workshop_id=workshop.id,
                store_id=store.id,
                bicycle_id=form.bicycle_id.data,
                status=form.status.data,
                notes=form.notes.data,
                estimated_delivery_at=form.estimated_delivery_at.data,
                service_type_ids=form.service_type_ids.data,
                parts_data=parts,
                service_prices=service_prices,
            )
            flash("Trabajo creado", "success")
            return redirect(url_for("main.jobs"))

    if request.method == "POST" and form.errors:
        flash("Revisa los campos ingresados", "error")
    
    selected_ids = set(form.service_type_ids.data or [])
    bicycle_options = [{"id": bid, "label": label} for bid, label in choices]
    
    # Logic for parts data repopulation
    if request.method == "POST":
        # We need a way to preserve entered parts if validation fails.
        # Ideally, we should use the parsed parts or raw form data.
        # Using a helper or raw extraction.
        # For simplicity in this refactor, we can re-parse or extract raw.
        # We'll re-use _parts_from_form logic but safely.
        # Actually `JobService.parse_job_parts` returns cleaned parts.
        # If error, we might want raw input? 
        # The original code had `_parts_from_form`.
        # I'll implement a simple one here locally or use the one from helper if I kept it (I didn't).
        pass

    parts_data = []
    if request.method == "POST":
         # Extract raw list
        descriptions = request.form.getlist("part_description")
        quantities = request.form.getlist("part_quantity")
        prices = request.form.getlist("part_unit_price")
        kinds = request.form.getlist("part_kind")
        count = max(len(descriptions), len(quantities), len(prices), len(kinds), 1)
        parts_data = []
        for idx in range(count):
            desc = descriptions[idx] if idx < len(descriptions) else ""
            qty = quantities[idx] if idx < len(quantities) else ""
            price = prices[idx] if idx < len(prices) else ""
            kind = kinds[idx] if idx < len(kinds) else "part"
            parts_data.append({
                "description": desc,
                "quantity": qty,
                "unit_price": price,
                "kind": kind
            })
            
    return render_template(
        "main/jobs/form.html",
        form=form,
        services=services,
        selected_ids=selected_ids,
        bicycle_options=bicycle_options,
        selected_bicycle_label="",
        parts_data=parts_data,
        service_prices={},
        title="Nuevo trabajo",
        submit_label="Crear trabajo",
    )


@main_bp.route("/jobs/<int:job_id>/edit", methods=["GET", "POST"])
@login_required
def jobs_edit(job_id):
    workshop, redirect_response = get_workshop_or_redirect()
    if redirect_response:
        return redirect_response

    store, store_redirect = get_store_or_redirect()
    if store_redirect:
        return store_redirect

    job = Job.query.filter_by(
        id=job_id, workshop_id=workshop.id, store_id=store.id
    ).first_or_404()
    
    form = JobForm()
    choices = bicycle_choices(workshop)
    form.bicycle_id.choices = choices
    services = services_list(workshop)
    form.service_type_ids.choices = [(service.id, service.name) for service in services]
    existing_items = {item.service_type_id: item for item in job.items}

    if request.method == "GET":
        form.bicycle_id.data = job.bicycle_id
        form.status.data = job.status
        form.notes.data = job.notes
        form.estimated_delivery_at.data = job.estimated_delivery_at
        form.service_type_ids.data = list(existing_items.keys())

    if form.validate_on_submit():
        parts, part_error = JobService.parse_job_parts(request.form)
        if part_error:
            flash(part_error, "error")
        else:
            service_prices = {}
            for sid in (form.service_type_ids.data or []):
                raw = request.form.get(f"service_price_{sid}", "")
                parsed = JobService.parse_decimal(raw)
                if parsed is not None:
                    service_prices[sid] = parsed
            JobService.update_job_full(
                job,
                bicycle_id=form.bicycle_id.data,
                status=form.status.data,
                notes=form.notes.data,
                estimated_delivery_at=form.estimated_delivery_at.data,
                service_type_ids=form.service_type_ids.data,
                parts_data=parts,
                service_prices=service_prices,
            )
            flash("Trabajo actualizado", "success")
            return redirect(url_for("main.jobs"))

    if request.method == "POST" and form.errors:
        flash("Revisa los campos ingresados", "error")
        
    selected_ids = set(form.service_type_ids.data or [])
    bicycle_options = [{"id": bid, "label": label} for bid, label in choices]
    selected_bicycle_label = ""
    for bid, label in choices:
        if bid == form.bicycle_id.data:
            selected_bicycle_label = label
            break

    if request.method == "POST":
         # Extract raw list again for re-render
        descriptions = request.form.getlist("part_description")
        quantities = request.form.getlist("part_quantity")
        prices = request.form.getlist("part_unit_price")
        kinds = request.form.getlist("part_kind")
        count = max(len(descriptions), len(quantities), len(prices), len(kinds), 1)
        parts_data = []
        for idx in range(count):
            desc = descriptions[idx] if idx < len(descriptions) else ""
            qty = quantities[idx] if idx < len(quantities) else ""
            price = prices[idx] if idx < len(prices) else ""
            kind = kinds[idx] if idx < len(kinds) else "part"
            parts_data.append({
                "description": desc,
                "quantity": qty,
                "unit_price": price,
                "kind": kind
            })
    else:
        parts_data = [
            {
                "description": part.description,
                "quantity": str(part.quantity),
                "unit_price": format_currency(part.unit_price),
                "kind": part.kind,
            }
            for part in job.parts
        ]
        if not parts_data:
            parts_data = []

    service_prices = {item.service_type_id: item.unit_price for item in job.items}

    return render_template(
        "main/jobs/form.html",
        form=form,
        services=services,
        selected_ids=selected_ids,
        bicycle_options=bicycle_options,
        selected_bicycle_label=selected_bicycle_label,
        parts_data=parts_data,
        service_prices=service_prices,
        title="Editar trabajo",
        submit_label="Guardar cambios",
    )


@main_bp.route("/jobs/<int:job_id>/status", methods=["POST"])
@login_required
def jobs_status(job_id):
    workshop, redirect_response = get_workshop_or_redirect()
    if redirect_response:
        return redirect_response

    store, store_redirect = get_store_or_redirect()
    if store_redirect:
        return store_redirect

    form = JobStatusForm()
    if not form.validate_on_submit():
        return redirect(url_for("main.jobs"))

    job = Job.query.filter_by(
        id=job_id, workshop_id=workshop.id, store_id=store.id
    ).first_or_404()
    
    job.status = form.status.data
    AuditService.log_action(
        "update",
        "job",
        job.id,
        f"Trabajo {job.code} -> {job.status}",
        workshop_id=workshop.id,
        store_id=store.id,
    )
    db.session.commit()
    flash("Estado actualizado correctamente", "success")
    return redirect(url_for("main.jobs"))


@main_bp.route("/jobs/<int:job_id>/pdf")
@login_required
def jobs_pdf(job_id):
    workshop, redirect_response = get_workshop_or_redirect()
    if redirect_response:
        return redirect_response

    store, store_redirect = get_store_or_redirect()
    if store_redirect:
        return store_redirect

    job = Job.query.filter_by(
        id=job_id, workshop_id=workshop.id, store_id=store.id
    ).first_or_404()

    if job.status not in ("ready", "closed"):
        flash("Solo se puede generar PDF para trabajos listos o cerrados", "error")
        return redirect(url_for("main.jobs_detail", job_id=job.id))

    service_total = sum(
        (item.unit_price or 0) * (item.quantity or 0) for item in job.items
    )
    parts_total = sum(
        (part.unit_price or 0) * (part.quantity or 0) for part in job.parts
    )
    total = service_total + parts_total

    buf = generate_job_pdf(job, service_total, parts_total, total)
    filename = build_pdf_filename(job)

    return send_file(
        buf,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=filename,
    )


@main_bp.route("/jobs/<int:job_id>/delete", methods=["POST"])
@login_required
def jobs_delete(job_id):
    workshop, redirect_response = get_workshop_or_redirect()
    if redirect_response:
        return redirect_response

    store, store_redirect = get_store_or_redirect()
    if store_redirect:
        return store_redirect

    form = DeleteForm()
    if not form.validate_on_submit():
        return redirect(url_for("main.jobs"))

    job = Job.query.filter_by(
        id=job_id, workshop_id=workshop.id, store_id=store.id
    ).first_or_404()
    
    if job.status == "in_progress":
        flash("No puedes eliminar un trabajo en proceso", "error")
        return redirect(url_for("main.jobs"))
        
    JobService.delete_job(job)
    flash("Trabajo eliminado", "success")
    return redirect(url_for("main.jobs"))
