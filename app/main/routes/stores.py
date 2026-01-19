from flask import render_template, request, redirect, url_for, flash, g, session
from flask_login import login_required
from app.main import main_bp
from app.extensions import db
from app.models import Store, Job, User
from app.services.audit_service import AuditService
from app.main.forms import StoreForm
from app.main.helpers import (
    get_workshop_or_redirect,
    owner_or_redirect
)

@main_bp.route("/stores", methods=["GET", "POST"])
@login_required
def stores():
    workshop, redirect_response = get_workshop_or_redirect()
    if redirect_response:
        return redirect_response

    _, owner_redirect = owner_or_redirect()
    if owner_redirect:
        return owner_redirect

    form = StoreForm()
    if form.validate_on_submit():
        store = Store(workshop_id=workshop.id, name=form.name.data)
        db.session.add(store)
        db.session.flush()
        AuditService.log_action(
            "create",
            "store",
            store.id,
            f"Sucursal {store.name}",
            workshop_id=workshop.id,
        )
        db.session.commit()
        if not session.get("active_store_id"):
            session["active_store_id"] = store.id
        flash("Sucursal creada", "success")
        return redirect(url_for("main.stores"))

    if request.method == "POST" and form.errors:
        flash("Revisa los campos ingresados", "error")

    stores_list = (
        Store.query.filter_by(workshop_id=workshop.id)
        .order_by(Store.name.asc())
        .all()
    )
    return render_template(
        "main/stores/index.html",
        form=form,
        stores=stores_list,
        active_store=g.active_store,
    )


@main_bp.route("/stores/<int:store_id>")
@login_required
def stores_detail(store_id):
    workshop, redirect_response = get_workshop_or_redirect()
    if redirect_response:
        return redirect_response

    _, owner_redirect = owner_or_redirect()
    if owner_redirect:
        return owner_redirect

    store = Store.query.filter_by(id=store_id, workshop_id=workshop.id).first_or_404()
    created_at, created_by, updated_at, updated_by = AuditService.get_audit_info(
        "store",
        store.id,
        fallback_created_at=store.created_at,
    )
    users_count = User.query.filter_by(store_id=store.id).count()
    jobs_count = Job.query.filter_by(workshop_id=workshop.id, store_id=store.id).count()
    return render_template(
        "main/stores/detail.html",
        store=store,
        created_at=created_at,
        created_by=created_by,
        updated_at=updated_at,
        updated_by=updated_by,
        users_count=users_count,
        jobs_count=jobs_count,
    )


@main_bp.route("/stores/<int:store_id>/edit", methods=["GET", "POST"])
@login_required
def stores_edit(store_id):
    workshop, redirect_response = get_workshop_or_redirect()
    if redirect_response:
        return redirect_response

    _, owner_redirect = owner_or_redirect()
    if owner_redirect:
        return owner_redirect

    store = Store.query.filter_by(id=store_id, workshop_id=workshop.id).first_or_404()
    form = StoreForm()
    if request.method == "GET":
        form.name.data = store.name

    if form.validate_on_submit():
        store.name = form.name.data
        AuditService.log_action(
            "update",
            "store",
            store.id,
            f"Sucursal {store.name}",
            workshop_id=workshop.id,
        )
        db.session.commit()
        flash("Sucursal actualizada", "success")
        return redirect(url_for("main.stores_detail", store_id=store.id))

    if request.method == "POST" and form.errors:
        flash("Revisa los campos ingresados", "error")

    return render_template(
        "main/stores/form.html",
        form=form,
        store=store,
        title="Editar sucursal",
        submit_label="Guardar cambios",
    )


@main_bp.route("/stores/switch", methods=["POST"])
@login_required
def stores_switch():
    workshop, redirect_response = get_workshop_or_redirect()
    if redirect_response:
        return redirect_response

    _, owner_redirect = owner_or_redirect()
    if owner_redirect:
        return owner_redirect

    store_id = request.form.get("store_id", type=int)
    store = Store.query.filter_by(id=store_id, workshop_id=workshop.id).first()
    if not store:
        flash("Sucursal invalida", "error")
        return redirect(request.referrer or url_for("main.dashboard"))

    session["active_store_id"] = store.id
    flash("Sucursal actualizada", "success")
    return redirect(request.referrer or url_for("main.dashboard"))
