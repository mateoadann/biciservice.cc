from datetime import date, timedelta
from decimal import Decimal

from app.extensions import db
from app.models import Bicycle, Client, Job, JobItem, ServiceType


def _create_job(owner_user, *, code, status, delivery_offset_days=0):
    workshop = owner_user.workshops[0]
    store = owner_user.store

    client = Client()
    client.workshop_id = workshop.id
    client.client_code = f"C{code}"
    client.full_name = f"Cliente {code}"
    client.email = f"cliente-{code.lower()}@example.com"

    bicycle = Bicycle()
    bicycle.workshop_id = workshop.id
    bicycle.client = client
    bicycle.brand = "Bianchi"
    bicycle.model = f"Modelo {code}"

    service = ServiceType()
    service.workshop_id = workshop.id
    service.name = f"Service {code}"
    service.base_price = Decimal("5000.00")

    job = Job()
    job.workshop_id = workshop.id
    job.store_id = store.id
    job.bicycle = bicycle
    job.code = code
    job.status = status
    job.notes = ""
    job.estimated_delivery_at = date.today() + timedelta(days=delivery_offset_days)

    item = JobItem()
    item.job = job
    item.service_type = service
    item.quantity = 1
    item.unit_price = Decimal("5000.00")

    db.session.add_all([client, bicycle, service, job, item])
    db.session.commit()
    return job


def test_jobs_status_filter_applies_on_server(client, owner_user, login):
    _create_job(owner_user, code="F001", status="ready", delivery_offset_days=1)
    _create_job(owner_user, code="F002", status="open", delivery_offset_days=1)
    login(owner_user.email, "Password1")

    response = client.get("/jobs?status=ready")
    assert response.status_code == 200

    html = response.get_data(as_text=True)
    assert "F001" in html
    assert "F002" not in html
    assert 'option value="ready" selected' in html


def test_jobs_overdue_filter_applies_on_server(client, owner_user, login):
    _create_job(owner_user, code="F101", status="open", delivery_offset_days=-1)
    _create_job(owner_user, code="F102", status="in_progress", delivery_offset_days=-2)
    _create_job(owner_user, code="F103", status="ready", delivery_offset_days=2)
    _create_job(owner_user, code="F104", status="closed", delivery_offset_days=-3)
    login(owner_user.email, "Password1")

    response = client.get("/jobs?status=overdue")
    assert response.status_code == 200

    html = response.get_data(as_text=True)
    assert "F101" in html
    assert "F102" in html
    assert "F103" not in html
    assert "F104" not in html
    assert 'option value="overdue" selected' in html


def test_jobs_status_filter_without_results_keeps_header_and_filters(client, owner_user, login):
    _create_job(owner_user, code="F201", status="open", delivery_offset_days=1)
    login(owner_user.email, "Password1")

    response = client.get("/jobs?status=cancelled")
    assert response.status_code == 200

    html = response.get_data(as_text=True)
    assert 'class="panel-header"' in html
    assert 'class="table-filters"' in html
    assert "No se encontraron trabajos con ese estado." in html
