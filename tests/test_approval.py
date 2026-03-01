from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from app.extensions import db
from app.models import (
    Bicycle,
    Client,
    Job,
    JobItem,
    JobPart,
    ServiceType,
    Store,
    User,
    Workshop,
)


def _create_dashboard_job(owner_user, *, code, created_at, service_price, part_price="0.00"):
    workshop = owner_user.workshops[0]
    store = owner_user.store

    client = Client()
    client.workshop_id = workshop.id
    client.client_code = f"C{code}"
    client.full_name = f"Cliente {code}"

    bicycle = Bicycle()
    bicycle.workshop_id = workshop.id
    bicycle.client = client
    bicycle.brand = "Trek"
    bicycle.model = f"Modelo {code}"

    service = ServiceType()
    service.workshop_id = workshop.id
    service.name = f"Service {code}"
    service.base_price = Decimal(service_price)

    job = Job()
    job.workshop_id = workshop.id
    job.store_id = store.id
    job.bicycle = bicycle
    job.code = code
    job.status = "closed"
    job.estimated_delivery_at = date.today()

    item = JobItem()
    item.job = job
    item.service_type = service
    item.quantity = 1
    item.unit_price = Decimal(service_price)

    db.session.add_all([client, bicycle, service, job, item])
    db.session.flush()

    if Decimal(part_price) > 0:
        part = JobPart()
        part.job = job
        part.description = f"Parte {code}"
        part.quantity = 1
        part.unit_price = Decimal(part_price)
        db.session.add(part)

    job.created_at = created_at
    db.session.commit()

    return job


def test_login_rejects_user_pending_approval(owner_user, login):
    owner_user.is_approved = False
    db.session.commit()

    response = login(owner_user.email, "Password1")
    assert response.status_code == 200
    assert b"pendiente de aprobacion" in response.data


def test_login_allows_approved_user(owner_user, login):
    owner_user.is_approved = True
    db.session.commit()

    response = login(owner_user.email, "Password1")
    assert response.status_code == 200
    assert b"Dashboard" in response.data


def test_login_two_factor_rejects_user_pending_approval(client, owner_user):
    owner_user.is_approved = False
    owner_user.two_factor_enabled = True
    owner_user.two_factor_secret = "JBSWY3DPEHPK3PXP"
    db.session.commit()

    with client.session_transaction() as session_data:
        session_data["pending_2fa_user_id"] = owner_user.id
        session_data["pending_2fa_remember"] = False

    response = client.get("/login/2fa", follow_redirects=True)
    assert response.status_code == 200
    assert b"pendiente de aprobacion" in response.data


def test_register_creates_owner_not_approved(client):
    response = client.post(
        "/register",
        data={
            "full_name": "Nuevo Owner",
            "email": "nuevo-owner@example.com",
            "workshop_name": "Taller Nuevo",
            "password": "Password1",
            "confirm": "Password1",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    user = User.query.filter_by(email="nuevo-owner@example.com").first()
    assert user is not None
    assert user.role == "owner"
    assert user.is_approved is False
    assert user.approved_at is None


def test_super_admin_pending_list_approve_and_reject(
    client, create_owner_user, create_super_admin_user, login
):
    super_admin = create_super_admin_user(email="root-approval@example.com")
    pending_owner = create_owner_user(
        email="pending-owner@example.com",
        is_approved=False,
        email_confirmed=True,
    )
    reject_owner = create_owner_user(
        email="reject-owner@example.com",
        is_approved=False,
        email_confirmed=True,
    )

    login(super_admin.email, "Password1")

    pending_response = client.get("/admin/pending")
    assert pending_response.status_code == 200
    assert b"pending-owner@example.com" in pending_response.data
    assert b"reject-owner@example.com" in pending_response.data

    approve_response = client.post(
        f"/admin/pending/{pending_owner.id}/approve", follow_redirects=True
    )
    assert approve_response.status_code == 200

    rejected_response = client.post(
        f"/admin/pending/{reject_owner.id}/reject", follow_redirects=True
    )
    assert rejected_response.status_code == 200

    approved_user = db.session.get(User, pending_owner.id)
    rejected_user = db.session.get(User, reject_owner.id)
    assert approved_user.is_approved is True
    assert approved_user.approved_at is not None
    assert rejected_user.is_active is False
    assert rejected_user.is_approved is False


def test_super_admin_can_delete_rejected_owner_with_workshop_and_store(
    client, create_owner_user, create_super_admin_user, login
):
    super_admin = create_super_admin_user(email="root-delete@example.com")
    rejected_owner = create_owner_user(
        email="delete-owner@example.com",
        is_approved=False,
        is_active=False,
    )
    workshop_id = rejected_owner.workshops[0].id
    store_id = rejected_owner.store_id

    login(super_admin.email, "Password1")
    response = client.post(
        f"/admin/owners/{rejected_owner.id}/delete", follow_redirects=True
    )
    assert response.status_code == 200

    assert db.session.get(User, rejected_owner.id) is None
    assert db.session.get(Workshop, workshop_id) is None
    assert db.session.get(Store, store_id) is None


def test_super_admin_dashboard_shows_pending_count(
    client, create_owner_user, create_super_admin_user, login
):
    super_admin = create_super_admin_user(email="root-metrics@example.com")
    create_owner_user(email="pending-metric@example.com", is_approved=False, is_active=True)
    create_owner_user(email="rejected-metric@example.com", is_approved=False, is_active=False)
    create_owner_user(email="approved-metric@example.com", is_approved=True, is_active=True)

    login(super_admin.email, "Password1")
    response = client.get("/admin/dashboard")

    assert response.status_code == 200
    assert b"Pendientes" in response.data
    assert b">1<" in response.data


def test_super_admin_dashboard_month_metrics_and_new_stats(
    client, create_owner_user, create_super_admin_user, login
):
    super_admin = create_super_admin_user(email="root-monthly@example.com")
    owner = create_owner_user(email="owner-monthly@example.com", is_approved=True)

    now_utc = datetime.now(timezone.utc)
    current_month_dt = now_utc.replace(day=10, hour=12, minute=0, second=0, microsecond=0)
    previous_month_dt = current_month_dt - timedelta(days=40)
    selected_month = current_month_dt.strftime("%Y-%m")

    _create_dashboard_job(
        owner,
        code="M001",
        created_at=current_month_dt,
        service_price="10000.00",
        part_price="5000.00",
    )
    _create_dashboard_job(
        owner,
        code="M002",
        created_at=current_month_dt,
        service_price="5000.00",
        part_price="0.00",
    )
    _create_dashboard_job(
        owner,
        code="M003",
        created_at=previous_month_dt,
        service_price="9000.00",
        part_price="0.00",
    )

    login(super_admin.email, "Password1")
    response = client.get(f"/admin/dashboard?month={selected_month}")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Owners" in html
    assert "Pendientes" in html
    assert "Talleres" not in html
    assert "Sucursales" not in html
    assert "Ingresos del mes" in html
    assert "20.000,00" in html
    assert "Trabajo promedio" in html
    assert "10.000,00" in html
    assert "Service promedio" in html
    assert "7.500,00" in html
