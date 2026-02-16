from datetime import date, datetime

from flask import render_template, redirect, url_for, g, flash, request
from flask_login import login_required, current_user
from sqlalchemy import func
from app.main import main_bp
from app.extensions import db
from app.models import Client, Bicycle, ServiceType, Job, JobItem, JobPart, Store
from app.main.helpers import (
    get_workshop_or_redirect,
    owner_or_redirect
)


def _parse_date_param(value: str | None) -> date | None:
    raw = (value or "").strip()
    if not raw:
        return None
    try:
        return datetime.strptime(raw, "%Y-%m-%d").date()
    except ValueError:
        return None

@main_bp.route("/")
def index():
    return redirect(url_for("main.dashboard"))


@main_bp.route("/dashboard")
@login_required
def dashboard():
    workshop = g.active_workshop
    store = g.active_store
    today = date.today()
    date_from = _parse_date_param(request.args.get("date_from"))
    date_to = _parse_date_param(request.args.get("date_to"))
    if date_from and date_to and date_from > date_to:
        date_from, date_to = date_to, date_from
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
        "revenue_closed": 0,
        "open": 0,
        "in_progress": 0,
        "ready": 0,
        "closed": 0,
        "cancelled": 0,
        "services_active": 0,
        "ready_for_delivery": 0,
        "overdue": 0,
        "total_jobs": 0,
        "close_rate": 0,
        "open_pct": 0,
        "in_progress_pct": 0,
        "ready_pct": 0,
        "closed_pct": 0,
        "cancelled_pct": 0,
        "date_from": date_from.isoformat() if date_from else "",
        "date_to": date_to.isoformat() if date_to else "",
        "has_active_range": bool(date_from or date_to),
    }
    if workshop and store:
        date_filters = []
        if date_from:
            date_filters.append(func.date(Job.created_at) >= date_from)
        if date_to:
            date_filters.append(func.date(Job.created_at) <= date_to)

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
            .filter(Job.workshop_id == workshop.id, Job.store_id == store.id, *date_filters)
            .scalar()
        )
        parts_revenue = (
            db.session.query(
                func.coalesce(func.sum(JobPart.unit_price * JobPart.quantity), 0)
            )
            .join(Job, Job.id == JobPart.job_id)
            .filter(Job.workshop_id == workshop.id, Job.store_id == store.id, *date_filters)
            .scalar()
        )
        revenue = service_revenue + parts_revenue
        service_revenue_closed = (
            db.session.query(
                func.coalesce(func.sum(JobItem.unit_price * JobItem.quantity), 0)
            )
            .join(Job, Job.id == JobItem.job_id)
            .filter(
                Job.workshop_id == workshop.id,
                Job.store_id == store.id,
                Job.status == "closed",
                *date_filters,
            )
            .scalar()
        )
        parts_revenue_closed = (
            db.session.query(
                func.coalesce(func.sum(JobPart.unit_price * JobPart.quantity), 0)
            )
            .join(Job, Job.id == JobPart.job_id)
            .filter(
                Job.workshop_id == workshop.id,
                Job.store_id == store.id,
                Job.status == "closed",
                *date_filters,
            )
            .scalar()
        )
        revenue_closed = service_revenue_closed + parts_revenue_closed
        status_counts = dict(
            db.session.query(Job.status, func.count(Job.id))
            .filter(Job.workshop_id == workshop.id, Job.store_id == store.id, *date_filters)
            .group_by(Job.status)
            .all()
        )
        open_jobs = status_counts.get("open", 0)
        in_progress_jobs = status_counts.get("in_progress", 0)
        ready_jobs = status_counts.get("ready", 0)
        closed_jobs = status_counts.get("closed", 0)
        cancelled_jobs = status_counts.get("cancelled", 0)
        total_jobs = open_jobs + in_progress_jobs + ready_jobs + closed_jobs + cancelled_jobs
        ready_for_delivery = (
            Job.query.filter(
                Job.workshop_id == workshop.id,
                Job.store_id == store.id,
                Job.status == "ready",
            ).count()
        )
        overdue_jobs = (
            Job.query.filter(
                Job.workshop_id == workshop.id,
                Job.store_id == store.id,
                Job.status.in_(["open", "in_progress", "ready"]),
                Job.estimated_delivery_at < today,
            ).count()
        )

        summary = {
            "revenue": revenue,
            "revenue_closed": revenue_closed,
            "open": open_jobs,
            "in_progress": in_progress_jobs,
            "ready": ready_jobs,
            "closed": closed_jobs,
            "cancelled": cancelled_jobs,
            "services_active": ServiceType.query.filter_by(
                workshop_id=workshop.id, is_active=True
            ).count(),
            "ready_for_delivery": ready_for_delivery,
            "overdue": overdue_jobs,
            "total_jobs": total_jobs,
            "close_rate": round((closed_jobs / total_jobs) * 100) if total_jobs else 0,
            "open_pct": round((open_jobs / total_jobs) * 100) if total_jobs else 0,
            "in_progress_pct": round((in_progress_jobs / total_jobs) * 100)
            if total_jobs
            else 0,
            "ready_pct": round((ready_jobs / total_jobs) * 100) if total_jobs else 0,
            "closed_pct": round((closed_jobs / total_jobs) * 100) if total_jobs else 0,
            "cancelled_pct": round((cancelled_jobs / total_jobs) * 100)
            if total_jobs
            else 0,
            "date_from": date_from.isoformat() if date_from else "",
            "date_to": date_to.isoformat() if date_to else "",
            "has_active_range": bool(date_from or date_to),
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
    flash(
        "La auditoria global ya no esta disponible. Revisa la auditoria dentro de cada entidad.",
        "info",
    )
    return redirect(url_for("main.dashboard"))
