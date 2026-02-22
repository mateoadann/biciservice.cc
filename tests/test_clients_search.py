from app.extensions import db
from app.models import Client


def test_clients_search_finds_records_beyond_current_page(client, owner_user, login):
    workshop = owner_user.workshops[0]
    for index in range(1, 13):
        item = Client()
        item.workshop_id = workshop.id
        item.client_code = f"{index:03d}"
        item.full_name = f"Cliente {index:02d}"
        item.email = f"cliente{index:02d}@mail.com"
        item.phone = f"555{index:04d}"
        db.session.add(item)
    db.session.commit()

    login(owner_user.email, "Password1")
    page_one = client.get("/clients?page=1")
    assert page_one.status_code == 200
    assert "Cliente 12" not in page_one.get_data(as_text=True)

    response = client.get("/clients?q=Cliente 12")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Cliente 12" in html
    assert "Cliente 01" not in html


def test_clients_search_matches_code_email_and_phone(client, owner_user, login):
    workshop = owner_user.workshops[0]
    target = Client()
    target.workshop_id = workshop.id
    target.client_code = "ABC9"
    target.full_name = "Cliente Filtro"
    target.email = "filtro@example.com"
    target.phone = "1133344455"
    db.session.add(target)
    db.session.commit()

    login(owner_user.email, "Password1")

    by_code = client.get("/clients?q=abc9")
    assert by_code.status_code == 200
    assert "Cliente Filtro" in by_code.get_data(as_text=True)

    by_email = client.get("/clients?q=FILTRO@EXAMPLE.COM")
    assert by_email.status_code == 200
    assert "Cliente Filtro" in by_email.get_data(as_text=True)

    by_phone = client.get("/clients?q=333444")
    assert by_phone.status_code == 200
    assert "Cliente Filtro" in by_phone.get_data(as_text=True)
