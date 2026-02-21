from app.extensions import db
from app.models import Bicycle, Client


def test_bicycles_search_finds_records_from_other_pages(client, owner_user, login):
    workshop = owner_user.workshops[0]
    main_client = Client()
    main_client.workshop_id = workshop.id
    main_client.client_code = "B001"
    main_client.full_name = "Cliente Bike"
    db.session.add(main_client)
    db.session.flush()

    for index in range(1, 13):
        bike = Bicycle()
        bike.workshop_id = workshop.id
        bike.client_id = main_client.id
        bike.brand = "Trek"
        bike.model = f"Modelo {index:02d}"
        bike.description = f"Bicicleta de prueba {index:02d}"
        db.session.add(bike)
    db.session.commit()

    login(owner_user.email, "Password1")
    page_one = client.get("/bicycles?page=1")
    assert page_one.status_code == 200
    assert "Modelo 01" not in page_one.get_data(as_text=True)

    response = client.get("/bicycles?q=Modelo 01")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Modelo 01" in html
    assert "Modelo 12" not in html


def test_bicycles_search_supports_query_and_brand_filter(client, owner_user, login):
    workshop = owner_user.workshops[0]

    c1 = Client()
    c1.workshop_id = workshop.id
    c1.client_code = "B101"
    c1.full_name = "Juan Perez"
    c2 = Client()
    c2.workshop_id = workshop.id
    c2.client_code = "B102"
    c2.full_name = "Maria Gomez"
    db.session.add_all([c1, c2])
    db.session.flush()

    b1 = Bicycle()
    b1.workshop_id = workshop.id
    b1.client_id = c1.id
    b1.brand = "Trek"
    b1.model = "X-Caliber"
    b1.description = "Azul"

    b2 = Bicycle()
    b2.workshop_id = workshop.id
    b2.client_id = c2.id
    b2.brand = "Specialized"
    b2.model = "Rockhopper"
    b2.description = "Negra"
    db.session.add_all([b1, b2])
    db.session.commit()

    login(owner_user.email, "Password1")

    by_client = client.get("/bicycles?q=perez")
    assert by_client.status_code == 200
    by_client_html = by_client.get_data(as_text=True)
    assert "X-Caliber" in by_client_html
    assert "Rockhopper" not in by_client_html

    by_query_and_brand = client.get("/bicycles?q=rock&brand=specialized")
    assert by_query_and_brand.status_code == 200
    html = by_query_and_brand.get_data(as_text=True)
    assert "Rockhopper" in html
    assert "X-Caliber" not in html
