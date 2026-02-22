from datetime import date, timedelta
from decimal import Decimal

from app.extensions import db
from app.models import Bicycle, Client, Job, JobItem, ServiceType


def _create_job(owner_user, *, code, client_name, brand, model, status="open", delivery_offset_days=1):
    workshop = owner_user.workshops[0]
    store = owner_user.store

    client = Client()
    client.workshop_id = workshop.id
    client.client_code = f"C{code}"
    client.full_name = client_name
    db.session.add(client)
    db.session.flush()

    bicycle = Bicycle()
    bicycle.workshop_id = workshop.id
    bicycle.client_id = client.id
    bicycle.brand = brand
    bicycle.model = model
    db.session.add(bicycle)
    db.session.flush()

    job = Job()
    job.workshop_id = workshop.id
    job.store_id = store.id
    job.bicycle_id = bicycle.id
    job.code = code
    job.status = status
    job.notes = ""
    job.estimated_delivery_at = date.today() + timedelta(days=delivery_offset_days)
    db.session.add(job)
    db.session.flush()
    return job


def _add_service(job, workshop_id, service_name):
    service = ServiceType()
    service.workshop_id = workshop_id
    service.name = service_name
    service.base_price = Decimal("1000.00")
    db.session.add(service)
    db.session.flush()

    item = JobItem()
    item.job_id = job.id
    item.service_type_id = service.id
    item.quantity = 1
    item.unit_price = Decimal("1000.00")
    db.session.add(item)


def test_jobs_search_finds_records_beyond_current_page(client, owner_user, login):
    workshop = owner_user.workshops[0]
    for index in range(1, 13):
        job = _create_job(
            owner_user,
            code=f"J{index:03d}",
            client_name=f"Cliente Trabajo {index}",
            brand="Giant",
            model=f"Modelo {index}",
        )
        _add_service(job, workshop.id, f"Service {index}")
    db.session.commit()

    login(owner_user.email, "Password1")

    page_one = client.get("/jobs?page=1")
    assert page_one.status_code == 200
    assert "J001" not in page_one.get_data(as_text=True)

    response = client.get("/jobs?q=J001")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "J001" in html
    assert "J012" not in html


def test_jobs_search_matches_service_name_without_duplicates(client, owner_user, login):
    workshop = owner_user.workshops[0]
    job = _create_job(
        owner_user,
        code="DUP1",
        client_name="Cliente Duplicado",
        brand="Trek",
        model="Domane",
    )
    _add_service(job, workshop.id, "Lavado premium")
    _add_service(job, workshop.id, "Lavado express")
    db.session.commit()

    login(owner_user.email, "Password1")
    response = client.get("/jobs?q=lavado")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert html.count('data-status="') == 1


def test_jobs_search_combines_with_status_filters(client, owner_user, login):
    workshop = owner_user.workshops[0]
    job_overdue = _create_job(
        owner_user,
        code="OVD1",
        client_name="Juan Mora",
        brand="Scott",
        model="Aspect",
        status="open",
        delivery_offset_days=-1,
    )
    _add_service(job_overdue, workshop.id, "Frenos")

    job_not_overdue = _create_job(
        owner_user,
        code="OVD2",
        client_name="Juan Mora",
        brand="Scott",
        model="Scale",
        status="ready",
        delivery_offset_days=2,
    )
    _add_service(job_not_overdue, workshop.id, "Frenos")
    db.session.commit()

    login(owner_user.email, "Password1")
    response = client.get("/jobs?q=juan&status=overdue")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "OVD1" in html
    assert "OVD2" not in html
