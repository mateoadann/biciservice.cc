from decimal import Decimal

from app.extensions import db
from app.models import ServiceType


def _create_service(workshop_id: int, name: str, base_price: str) -> ServiceType:
    service = ServiceType()
    service.workshop_id = workshop_id
    service.name = name
    service.description = "Descripcion inicial"
    service.base_price = Decimal(base_price)
    service.is_active = True
    db.session.add(service)
    db.session.commit()
    return service


def test_services_edit_prefills_base_price(client, owner_user, login):
    workshop = owner_user.workshops[0]
    service = _create_service(workshop.id, "Mantenimiento", "12345.67")

    login(owner_user.email, "Password1")
    response = client.get(f"/services/{service.id}/edit")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'name="base_price"' in html
    price_input_chunk = html.split('name="base_price"', 1)[1][:180]
    assert 'type="text"' in price_input_chunk
    assert 'value="12.345,67"' in html


def test_services_edit_keeps_price_when_value_sent_unchanged(client, owner_user, login):
    workshop = owner_user.workshops[0]
    service = _create_service(workshop.id, "Ajuste general", "8000.00")

    login(owner_user.email, "Password1")
    response = client.post(
        f"/services/{service.id}/edit",
        data={
            "name": service.name,
            "description": "Descripcion actualizada",
            "base_price": "8.000,00",
            "is_active": "y",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    refreshed = db.session.get(ServiceType, service.id)
    assert refreshed is not None
    assert refreshed.base_price == Decimal("8000.00")
