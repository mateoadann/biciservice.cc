from app.extensions import db
from app.main.helpers import paginate_query
from app.models import Client


def test_paginate_query_caps_out_of_range_page(owner_user):
    workshop = owner_user.workshops[0]
    for idx in range(12):
        client = Client()
        client.workshop_id = workshop.id
        client.client_code = str(100 + idx)
        client.full_name = f"Cliente {idx}"
        client.email = f"cliente{idx}@example.com"
        db.session.add(client)
    db.session.commit()

    query = Client.query.filter_by(workshop_id=workshop.id).order_by(Client.id.asc())
    page = paginate_query(query, page=999, per_page=10)

    assert page["page"] == 2
    assert page["pages"] == 2
    assert page["start"] == 11
    assert page["end"] == 12
    assert len(page["items"]) == 2
    assert page["has_prev"] is True
    assert page["has_next"] is False
