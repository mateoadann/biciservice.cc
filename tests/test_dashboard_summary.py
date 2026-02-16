from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from app.extensions import db
from app.models import Bicycle, Client, Job, JobItem, ServiceType


def _create_job(
    owner_user,
    *,
    code,
    status,
    delivery_offset_days=0,
    amount="10000.00",
    created_offset_days=0,
):
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
    bicycle.brand = "Trek"
    bicycle.model = f"Modelo {code}"

    service = ServiceType()
    service.workshop_id = workshop.id
    service.name = f"Service {code}"
    service.base_price = Decimal(amount)

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
    item.unit_price = Decimal(amount)

    db.session.add_all([client, bicycle, service, job, item])
    db.session.commit()

    if created_offset_days:
        job.created_at = datetime.now(timezone.utc) + timedelta(days=created_offset_days)
        db.session.commit()

    return job


def test_dashboard_summary_without_jobs(client, owner_user, login):
    login(owner_user.email, "Password1")

    response = client.get("/dashboard")
    assert response.status_code == 200

    html = response.get_data(as_text=True)
    assert "Tasa de cierre" in html
    assert "Estado de trabajos (0)" in html
    assert "Aun no hay trabajos registrados. Crea tu primer trabajo para comenzar." in html


def test_dashboard_summary_shows_overdue_and_ready_alerts(client, owner_user, login):
    _create_job(owner_user, code="D001", status="open", delivery_offset_days=-1)
    _create_job(owner_user, code="D002", status="ready", delivery_offset_days=1)
    login(owner_user.email, "Password1")

    response = client.get("/dashboard")
    assert response.status_code == 200

    html = response.get_data(as_text=True)
    assert "Estado de trabajos (2)" in html
    assert "Hay 1 trabajo(s) atrasado(s)." in html
    assert "Tienes 1 trabajo(s) listo(s) para entrega." in html
    assert "status=overdue" in html
    assert "status=ready" in html


def test_dashboard_summary_calculates_closed_revenue_and_close_rate(client, owner_user, login):
    _create_job(owner_user, code="D101", status="closed", amount="20000.00")
    _create_job(owner_user, code="D102", status="open", amount="10000.00")
    login(owner_user.email, "Password1")

    response = client.get("/dashboard")
    assert response.status_code == 200

    html = response.get_data(as_text=True)
    assert "Ingresos cerrados" in html
    assert "20.000,00" in html
    assert "30.000,00" in html
    assert "Tasa de cierre" in html
    assert "50%" in html
    assert "Cerrados: 1" in html


def test_dashboard_summary_applies_date_range_to_metrics(client, owner_user, login):
    _create_job(
        owner_user,
        code="D201",
        status="closed",
        amount="20000.00",
        created_offset_days=-20,
    )
    _create_job(
        owner_user,
        code="D202",
        status="open",
        amount="10000.00",
        created_offset_days=0,
    )
    login(owner_user.email, "Password1")

    today = date.today().isoformat()
    response = client.get(f"/dashboard?date_from={today}&date_to={today}")
    assert response.status_code == 200

    html = response.get_data(as_text=True)
    assert "Periodo aplicado" in html
    assert f'value="{today}"' in html
    assert "Estado de trabajos en periodo (1)" in html
    assert "10.000,00" in html
    assert "Ingresos cerrados" in html
    assert "0,00" in html


def test_dashboard_summary_includes_cancelled_in_distribution(client, owner_user, login):
    _create_job(owner_user, code="D301", status="closed", amount="12000.00")
    _create_job(owner_user, code="D302", status="cancelled", amount="7000.00")
    login(owner_user.email, "Password1")

    response = client.get("/dashboard")
    assert response.status_code == 200

    html = response.get_data(as_text=True)
    assert "Cancelados: 1" in html
    assert "Tasa de cierre" in html
    assert "50%" in html
