from datetime import date
from decimal import Decimal

from app.extensions import db
from app.models import Bicycle, Client, Job, JobItem, ServiceType


def _create_job(owner_user, *, code, status="ready", notes=""):
    workshop = owner_user.workshops[0]
    store = owner_user.store

    client = Client()
    client.workshop_id = workshop.id
    client.client_code = "100"
    client.full_name = "Cliente PDF"
    client.email = "cliente-pdf@example.com"

    bicycle = Bicycle()
    bicycle.workshop_id = workshop.id
    bicycle.client = client
    bicycle.brand = "Trek"
    bicycle.model = "Marlin"

    service = ServiceType()
    service.workshop_id = workshop.id
    service.name = "Ajuste general"
    service.base_price = Decimal("15000.00")

    job = Job()
    job.workshop_id = workshop.id
    job.store_id = store.id
    job.bicycle = bicycle
    job.code = code
    job.status = status
    job.notes = notes
    job.estimated_delivery_at = date.today()

    item = JobItem()
    item.job = job
    item.service_type = service
    item.quantity = 1
    item.unit_price = Decimal("15000.00")

    db.session.add_all([client, bicycle, service, job, item])
    db.session.commit()
    return job


def test_jobs_pdf_returns_pdf_for_ready_job(client, owner_user, login):
    job = _create_job(owner_user, code="P001", status="ready")
    login(owner_user.email, "Password1")

    response = client.get(f"/jobs/{job.id}/pdf")
    assert response.status_code == 200
    assert response.mimetype == "application/pdf"
    assert response.data.startswith(b"%PDF")
    assert "attachment;" in response.headers.get("Content-Disposition", "")


def test_jobs_pdf_rejects_open_job(client, owner_user, login):
    job = _create_job(owner_user, code="P002", status="open")
    login(owner_user.email, "Password1")

    response = client.get(f"/jobs/{job.id}/pdf", follow_redirects=False)
    assert response.status_code == 302
    assert f"/jobs/{job.id}" in response.headers.get("Location", "")

    detail_response = client.get(response.headers["Location"], follow_redirects=True)
    assert detail_response.status_code == 200
    assert b"Solo se puede generar PDF para trabajos listos o cerrados" in detail_response.data


def test_jobs_pdf_handles_special_characters_in_notes(client, owner_user, login):
    owner_user.workshops[0].name = "Taller & <Norte>"
    db.session.commit()

    job = _create_job(
        owner_user,
        code="P003",
        status="ready",
        notes="Observaciones con simbolos: & <etiqueta> > cierre",
    )
    login(owner_user.email, "Password1")

    response = client.get(f"/jobs/{job.id}/pdf")
    assert response.status_code == 200
    assert response.mimetype == "application/pdf"
    assert response.data.startswith(b"%PDF")
