from flask import render_template, redirect, url_for, g
from flask_login import login_required, current_user
from sqlalchemy import func
from app.main import main_bp
from app.extensions import db
from app.models import Client, Bicycle, ServiceType, Job, JobItem, JobPart, Store, AuditLog
from app.main.helpers import (
    get_workshop_or_redirect,
    owner_or_redirect
)

@main_bp.route("/")
def index():
    return redirect(url_for("main.dashboard"))


@main_bp.route("/dashboard")
@login_required
def dashboard():
    workshop = g.active_workshop
    store = g.active_store
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
        "jobs": Job.query.filter_by(workshop_id=workshop.id, store_id=store.id).count()
        if workshop and store
        else 0,
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
    if workshop and store:
        agenda_jobs = (
            Job.query.filter_by(workshop_id=workshop.id, store_id=store.id)
            .order_by(Job.created_at.desc())
            .limit(5)
            .all()
        )
        service_revenue = (
            db.session.query(
                func.coalesce(func.sum(JobItem.unit_price * JobItem.quantity), 0)
            )
            .join(Job, Job.id == JobItem.job_id)
            .filter(Job.workshop_id == workshop.id, Job.store_id == store.id)
            .scalar()
        )
        parts_revenue = (
            db.session.query(
                func.coalesce(func.sum(JobPart.unit_price * JobPart.quantity), 0)
            )
            .join(Job, Job.id == JobPart.job_id)
            .filter(Job.workshop_id == workshop.id, Job.store_id == store.id)
            .scalar()
        )
        revenue = service_revenue + parts_revenue
        status_counts = dict(
            db.session.query(Job.status, func.count(Job.id))
            .filter(Job.workshop_id == workshop.id, Job.store_id == store.id)
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
    elif workshop:
        summary["services_active"] = ServiceType.query.filter_by(
            workshop_id=workshop.id, is_active=True
        ).count()

    return render_template(
        "main/dashboard.html",
        counts=counts,
        workshop=workshop,
        agenda_jobs=agenda_jobs,
        summary=summary,
    )

@main_bp.route("/audit")
@login_required
def audit():
    _, owner_redirect = owner_or_redirect()
    if owner_redirect:
        return owner_redirect
    workshop = g.active_workshop
    logs = (
        AuditLog.query.filter_by(workshop_id=workshop.id)
        .order_by(AuditLog.created_at.desc())
        .limit(200)
        .all()
    )
    return render_template("main/audit/index.html", logs=logs)
