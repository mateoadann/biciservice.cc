from app.extensions import db
from app.models import Store, User, Workshop


def _create_owner_user():
    workshop = Workshop(name="Taller Test")
    store = Store(name="Sucursal principal", workshop=workshop)
    user = User(
        full_name="Owner Test",
        email="owner@example.com",
        role="owner",
        store=store,
        email_confirmed=True,
    )
    user.set_password("Password1")
    user.workshops.append(workshop)
    db.session.add_all([workshop, store, user])
    db.session.commit()
    return user


def test_login_page_loads(client):
    response = client.get("/login")
    assert response.status_code == 200


def test_dashboard_requires_login(client):
    response = client.get("/dashboard")
    assert response.status_code == 302
    assert "/login" in response.headers.get("Location", "")


def test_login_success_redirects(client):
    _create_owner_user()
    response = client.post(
        "/login",
        data={"email": "owner@example.com", "password": "Password1"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Dashboard" in response.data
