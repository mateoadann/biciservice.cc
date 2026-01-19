from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required
from app.main import main_bp
from app.models import Client
from app.services.client_service import ClientService
from app.services.audit_service import AuditService
from app.main.forms import ClientForm, DeleteForm
from app.main.helpers import get_workshop_or_redirect, paginate_query

@main_bp.route("/clients")
@login_required
def clients():
    workshop, redirect_response = get_workshop_or_redirect()
    if redirect_response:
        return redirect_response
    page = request.args.get("page", 1, type=int)
    query = Client.query.filter_by(workshop_id=workshop.id).order_by(Client.full_name.asc())
    pagination = paginate_query(query, page)
    return render_template(
        "main/clients/index.html",
        clients=pagination["items"],
        pagination=pagination,
        delete_form=DeleteForm(),
    )


@main_bp.route("/clients/<int:client_id>")
@login_required
def clients_detail(client_id):
    workshop, redirect_response = get_workshop_or_redirect()
    if redirect_response:
        return redirect_response
    client = Client.query.filter_by(id=client_id, workshop_id=workshop.id).first_or_404()
    created_at, created_by, updated_at, updated_by = AuditService.get_audit_info(
        "client",
        client.id,
        fallback_created_at=client.created_at,
    )
    return render_template(
        "main/clients/detail.html",
        client=client,
        created_at=created_at,
        created_by=created_by,
        updated_at=updated_at,
        updated_by=updated_by,
    )


@main_bp.route("/clients/new", methods=["GET", "POST"])
@login_required
def clients_create():
    workshop, redirect_response = get_workshop_or_redirect()
    if redirect_response:
        return redirect_response

    form = ClientForm()
    if form.validate_on_submit():
        ClientService.create_client(
            workshop_id=workshop.id,
            full_name=form.full_name.data,
            email=form.email.data,
            phone=form.phone.data
        )
        flash("Cliente creado", "success")
        return redirect(url_for("main.clients"))

    if request.method == "POST" and form.errors:
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
    workshop, redirect_response = get_workshop_or_redirect()
    if redirect_response:
        return redirect_response

    client = Client.query.filter_by(id=client_id, workshop_id=workshop.id).first_or_404()
    form = ClientForm()

    if request.method == "GET":
        form.full_name.data = client.full_name
        form.email.data = client.email
        form.phone.data = client.phone

    if form.validate_on_submit():
        ClientService.update_client(
            client,
            full_name=form.full_name.data,
            email=form.email.data,
            phone=form.phone.data
        )
        flash("Cliente actualizado", "success")
        return redirect(url_for("main.clients"))

    if request.method == "POST" and form.errors:
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
    workshop, redirect_response = get_workshop_or_redirect()
    if redirect_response:
        return redirect_response

    form = DeleteForm()
    if not form.validate_on_submit():
        return redirect(url_for("main.clients"))

    client = Client.query.filter_by(id=client_id, workshop_id=workshop.id).first_or_404()
    if client.bicycles:
        flash("No se puede borrar un cliente con bicicletas", "error")
        return redirect(url_for("main.clients"))
        
    ClientService.delete_client(client)
    flash("Cliente eliminado", "success")
    return redirect(url_for("main.clients"))
