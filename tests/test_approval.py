from app.extensions import db
from app.models import Store, User, Workshop


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
