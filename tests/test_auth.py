from app.extensions import db


def test_login_page_loads(client):
    response = client.get("/login")
    assert response.status_code == 200


def test_dashboard_requires_login(client):
    response = client.get("/dashboard")
    assert response.status_code == 302
    assert "/login" in response.headers.get("Location", "")


def test_owner_login_success_redirects_dashboard(owner_user, login):
    response = login(owner_user.email, "Password1")
    assert response.status_code == 200
    assert b"Dashboard" in response.data


def test_super_admin_login_redirects_to_admin_dashboard(create_super_admin_user, login):
    super_admin = create_super_admin_user(email="root@example.com")
    response = login(super_admin.email, "Password1", follow_redirects=False)
    assert response.status_code == 302
    assert "/admin/dashboard" in response.headers.get("Location", "")


def test_login_rejects_unconfirmed_owner(owner_user, login):
    owner_user.email_confirmed = False
    db.session.commit()

    response = login(owner_user.email, "Password1")
    assert response.status_code == 200
    assert b"Email sin confirmar" in response.data


def test_login_rejects_inactive_user(owner_user, login):
    setattr(owner_user, "is_active", False)
    db.session.commit()

    response = login(owner_user.email, "Password1")
    assert response.status_code == 200
    assert b"Cuenta desactivada" in response.data
