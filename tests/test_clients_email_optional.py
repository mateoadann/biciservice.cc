from app.extensions import db
from app.models import Client


def test_clients_create_allows_empty_email(client, owner_user, login):
    login(owner_user.email, "Password1")

    response = client.post(
        "/clients/new",
        data={
            "full_name": "Cliente sin email",
            "email": "",
            "phone": "123456789",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Cliente creado" in response.data

    workshop = owner_user.workshops[0]
    created = Client.query.filter_by(
        workshop_id=workshop.id,
        full_name="Cliente sin email",
    ).first()
    assert created is not None
    assert created.email is None


def test_clients_edit_allows_clearing_email(client, owner_user, login):
    workshop = owner_user.workshops[0]
    existing = Client()
    existing.workshop_id = workshop.id
    existing.client_code = "100"
    existing.full_name = "Cliente con email"
    existing.email = "cliente@example.com"
    existing.phone = "111222333"
    db.session.add(existing)
    db.session.commit()

    login(owner_user.email, "Password1")
    response = client.post(
        f"/clients/{existing.id}/edit",
        data={
            "full_name": "Cliente con email",
            "email": "",
            "phone": "111222333",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Cliente actualizado" in response.data

    db.session.refresh(existing)
    assert existing.email is None


def test_clients_create_rejects_invalid_non_empty_email(client, owner_user, login):
    login(owner_user.email, "Password1")

    response = client.post(
        "/clients/new",
        data={
            "full_name": "Cliente email invalido",
            "email": "mail-invalido",
            "phone": "123456789",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Revisa los campos ingresados" in response.data
    assert b"Email invalido" in response.data

    workshop = owner_user.workshops[0]
    created = Client.query.filter_by(
        workshop_id=workshop.id,
        full_name="Cliente email invalido",
    ).first()
    assert created is None
