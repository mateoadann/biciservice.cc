from datetime import datetime, timezone

from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.main import main_bp
from app.extensions import db
from app.models import User, Store, user_workshops
from app.services.audit_service import AuditService
from app.main.forms import UserCreateForm, UserEditForm, DeleteForm
from app.main.helpers import (
    get_workshop_or_redirect,
    owner_or_redirect,
    store_choices
)

@main_bp.route("/users")
@login_required
def users():
    workshop, redirect_response = get_workshop_or_redirect()
    if redirect_response:
        return redirect_response

    _, owner_redirect = owner_or_redirect()
    if owner_redirect:
        return owner_redirect

    users_list = (
        User.query.join(user_workshops)
        .filter(user_workshops.c.workshop_id == workshop.id)
        .order_by(User.full_name.asc())
        .all()
    )
    return render_template(
        "main/users/index.html",
        users=users_list,
        delete_form=DeleteForm(),
    )


@main_bp.route("/users/<int:user_id>")
@login_required
def users_detail(user_id):
    workshop, redirect_response = get_workshop_or_redirect()
    if redirect_response:
        return redirect_response

    _, owner_redirect = owner_or_redirect()
    if owner_redirect:
        return owner_redirect

    user = (
        User.query.join(user_workshops)
        .filter(User.id == user_id, user_workshops.c.workshop_id == workshop.id)
        .first_or_404()
    )
    created_at, created_by, updated_at, updated_by = AuditService.get_audit_info(
        "user",
        user.id,
        fallback_created_at=user.created_at,
    )
    return render_template(
        "main/users/detail.html",
        user=user,
        created_at=created_at,
        created_by=created_by,
        updated_at=updated_at,
        updated_by=updated_by,
    )


@main_bp.route("/users/new", methods=["GET", "POST"])
@login_required
def users_create():
    workshop, redirect_response = get_workshop_or_redirect()
    if redirect_response:
        return redirect_response

    _, owner_redirect = owner_or_redirect()
    if owner_redirect:
        return owner_redirect

    choices = store_choices(workshop)
    if not choices:
        flash("Primero crea una sucursal", "error")
        return redirect(url_for("main.stores"))

    form = UserCreateForm()
    form.store_id.choices = choices

    if form.validate_on_submit():
        email = form.email.data.lower()
        if User.query.filter_by(email=email).first():
            flash("El email ya esta registrado", "error")
            return render_template(
                "main/users/form.html",
                form=form,
                title="Nuevo usuario",
                submit_label="Crear usuario",
            )

        store = Store.query.filter_by(id=form.store_id.data, workshop_id=workshop.id).first()
        if not store:
            flash("Sucursal invalida", "error")
            return redirect(url_for("main.users_create"))

        user = User(
            full_name=form.full_name.data,
            email=email,
            role=form.role.data,
            is_approved=True,
            approved_at=datetime.now(timezone.utc),
            store=store,
        )
        user.set_password(form.password.data)
        user.workshops.append(workshop)
        db.session.add(user)
        db.session.flush()
        AuditService.log_action(
            "create",
            "user",
            user.id,
            f"Usuario {user.full_name}",
            workshop_id=workshop.id,
        )
        db.session.commit()
        flash("Usuario creado", "success")
        return redirect(url_for("main.users"))

    if request.method == "POST" and form.errors:
        flash("Revisa los campos ingresados", "error")
    return render_template(
        "main/users/form.html",
        form=form,
        title="Nuevo usuario",
        submit_label="Crear usuario",
    )


@main_bp.route("/users/<int:user_id>/edit", methods=["GET", "POST"])
@login_required
def users_edit(user_id):
    workshop, redirect_response = get_workshop_or_redirect()
    if redirect_response:
        return redirect_response

    _, owner_redirect = owner_or_redirect()
    if owner_redirect:
        return owner_redirect

    user = (
        User.query.join(user_workshops)
        .filter(User.id == user_id, user_workshops.c.workshop_id == workshop.id)
        .first_or_404()
    )

    form = UserEditForm()
    form.store_id.choices = store_choices(workshop)

    if request.method == "GET":
        form.full_name.data = user.full_name
        form.email.data = user.email
        form.role.data = user.role
        form.store_id.data = user.store_id

    if form.validate_on_submit():
        email = form.email.data.lower()
        if email != user.email and User.query.filter_by(email=email).first():
            flash("El email ya esta registrado", "error")
            return render_template(
                "main/users/form.html",
                form=form,
                title="Editar usuario",
                submit_label="Guardar cambios",
            )

        if user.id == current_user.id and form.role.data != "owner":
            flash("No puedes quitarte el rol owner", "error")
            return redirect(url_for("main.users_edit", user_id=user.id))

        if user.role == "owner" and form.role.data != "owner":
            owner_count = (
                User.query.join(user_workshops)
                .filter(
                    user_workshops.c.workshop_id == workshop.id,
                    User.role == "owner",
                )
                .count()
            )
            if owner_count <= 1:
                flash("Debe existir al menos un owner", "error")
                return redirect(url_for("main.users_edit", user_id=user.id))

        store = Store.query.filter_by(id=form.store_id.data, workshop_id=workshop.id).first()
        if not store:
            flash("Sucursal invalida", "error")
            return redirect(url_for("main.users"))

        user.full_name = form.full_name.data
        user.email = email
        user.role = form.role.data
        user.store = store
        if form.password.data:
            user.set_password(form.password.data)

        AuditService.log_action(
            "update",
            "user",
            user.id,
            f"Usuario {user.full_name}",
            workshop_id=workshop.id,
        )
        db.session.commit()
        flash("Usuario actualizado", "success")
        return redirect(url_for("main.users"))

    if request.method == "POST" and form.errors:
        flash("Revisa los campos ingresados", "error")
    return render_template(
        "main/users/form.html",
        form=form,
        title="Editar usuario",
        submit_label="Guardar cambios",
    )


@main_bp.route("/users/<int:user_id>/delete", methods=["POST"])
@login_required
def users_delete(user_id):
    workshop, redirect_response = get_workshop_or_redirect()
    if redirect_response:
        return redirect_response

    _, owner_redirect = owner_or_redirect()
    if owner_redirect:
        return owner_redirect

    form = DeleteForm()
    if not form.validate_on_submit():
        return redirect(url_for("main.users"))

    user = (
        User.query.join(user_workshops)
        .filter(User.id == user_id, user_workshops.c.workshop_id == workshop.id)
        .first_or_404()
    )

    if user.id == current_user.id:
        flash("No puedes eliminar tu usuario", "error")
        return redirect(url_for("main.users"))

    if user.role == "owner":
        owner_count = (
            User.query.join(user_workshops)
            .filter(
                user_workshops.c.workshop_id == workshop.id,
                User.role == "owner",
            )
            .count()
        )
        if owner_count <= 1:
            flash("Debe existir al menos un owner", "error")
            return redirect(url_for("main.users"))

    db.session.execute(
        user_workshops.delete().where(user_workshops.c.user_id == user.id)
    )
    AuditService.log_action(
        "delete",
        "user",
        user.id,
        f"Usuario {user.full_name}",
        workshop_id=workshop.id,
    )
    db.session.delete(user)
    db.session.commit()
    flash("Usuario eliminado", "success")
    return redirect(url_for("main.users"))
