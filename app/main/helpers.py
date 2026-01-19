import math
import os
import re
import secrets
import string
from pathlib import Path
from uuid import uuid4
from decimal import Decimal, InvalidOperation

from flask import current_app, flash, g, redirect, url_for, session
from flask_login import current_user
from PIL import Image
from io import BytesIO

from ..models import Store, Client, Bicycle, ServiceType, Job
from .forms import BRAND_CHOICES

def validate_upload(file_storage):
    from werkzeug.utils import secure_filename
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


def save_upload(file_storage, workshop_id):
    if not file_storage:
        return None, None
    filename, error = validate_upload(file_storage)
    if error:
        return None, error
    upload_root = Path(current_app.config["UPLOAD_FOLDER"]) / str(workshop_id)
    upload_root.mkdir(parents=True, exist_ok=True)
    unique_name = f"{uuid4().hex}_{filename}"
    file_path = upload_root / unique_name
    file_storage.save(file_path)
    rel_path = os.path.relpath(file_path, Path(current_app.root_path).parent / "app/static") 
    # Note: original code used __file__ relative path. 
    # rel_path = os.path.relpath(file_path, Path(__file__).resolve().parent.parent / "static")
    # We need to ensure this path calculation is correct. 
    # If app.static_folder is set, usage of it is better.
    # In original: Path(__file__).resolve().parent.parent / "static" -> app/static
    # We will use current_app.static_folder if available or hardcode valid path relative to app root.
    
    # Let's try to match original behavior but robustly.
    static_folder = Path(current_app.static_folder)
    # file_path is absolute. 
    # We want relative path from static_folder.
    try:
        rel_path = file_path.relative_to(static_folder)
    except ValueError:
        # Fallback if static folder is not parent
        rel_path = unique_name
        
    return str(rel_path).replace(os.path.sep, "/"), None


def delete_upload(rel_path):
    if not rel_path:
        return
    file_path = Path(current_app.static_folder) / rel_path
    if file_path.exists():
        file_path.unlink()


def get_workshop_or_redirect():
    workshop = g.active_workshop
    if workshop is None:
        flash("No hay taller seleccionado", "error")
        return None, redirect(url_for("main.dashboard"))
    return workshop, None


def get_store_or_redirect():
    store = g.active_store
    if store is None:
        if current_user.role != "owner":
            flash("No tienes una sucursal asignada", "error")
            return None, redirect(url_for("main.dashboard"))
        flash("No hay sucursal seleccionada", "error")
        return None, redirect(url_for("main.stores"))
    return store, None


def owner_or_redirect():
    if current_user.role != "owner":
        flash("No tienes permisos para esta seccion", "error")
        return None, redirect(url_for("main.dashboard"))
    return True, None


def super_admin_or_redirect():
    if current_user.role != "super_admin":
        flash("No tienes permisos para esta seccion", "error")
        return None, redirect(url_for("main.dashboard"))
    return True, None


def paginate_query(query, page, per_page=10):
    safe_page = max(page, 1)
    total = query.count()
    pages = max(1, math.ceil(total / per_page)) if total else 1
    if safe_page > pages:
        safe_page = pages
    items = (
        query.offset((safe_page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    start = (safe_page - 1) * per_page + 1 if total else 0
    end = min(safe_page * per_page, total) if total else 0
    return {
        "items": items,
        "page": safe_page,
        "per_page": per_page,
        "total": total,
        "pages": pages,
        "has_prev": safe_page > 1,
        "has_next": safe_page < pages,
        "prev_num": safe_page - 1,
        "next_num": safe_page + 1,
        "start": start,
        "end": end,
    }


def generate_temp_password(length=12):
    alphabet = string.ascii_letters + string.digits
    while True:
        password = "".join(secrets.choice(alphabet) for _ in range(length))
        if (
            any(char.islower() for char in password)
            and any(char.isupper() for char in password)
            and any(char.isdigit() for char in password)
        ):
            return password

def client_choices(workshop):
    clients = (
        Client.query.filter_by(workshop_id=workshop.id)
        .order_by(Client.full_name.asc())
        .all()
    )
    return [(client.id, client.full_name) for client in clients]


def store_choices(workshop):
    stores = (
        Store.query.filter_by(workshop_id=workshop.id)
        .order_by(Store.name.asc())
        .all()
    )
    return [(store.id, store.name) for store in stores]


def bicycle_choices(workshop):
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


def service_choices(workshop):
    services = services_list(workshop)
    return [(service.id, service.name) for service in services]


def services_list(workshop):
    return (
        ServiceType.query.filter_by(workshop_id=workshop.id)
        .order_by(ServiceType.name.asc())
        .all()
    )

def brand_choices():
    return [("", "Seleccionar marca")] + [(brand, brand) for brand in BRAND_CHOICES]


def resolve_brand(form):
    return form.brand_select.data or None


def format_currency(value):
    if value is None:
        return ""
    try:
        if isinstance(value, Decimal):
            numeric = value
        else:
            numeric = Decimal(str(value))
        formatted = f"{numeric:,.2f}"
    except (InvalidOperation, ValueError, TypeError):
        return str(value)
    return formatted.replace(",", "X").replace(".", ",").replace("X", ".")
