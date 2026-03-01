from app.extensions import db
from app.models import User


def _create_staff_user(create_owner_user):
    owner = create_owner_user(email="owner-for-staff@example.com")
    workshop = owner.workshops[0]
    store = owner.store

    staff = User()
    staff.full_name = "Staff Test"
    staff.email = "staff@example.com"
    staff.role = "staff"
    staff.store_id = store.id
    staff.email_confirmed = True
    staff.is_active = True
    staff.is_approved = True
    staff.set_password("Password1")
    staff.workshops.append(workshop)

    db.session.add(staff)
    db.session.commit()
    return staff


def test_owner_sees_tour_prompt_on_first_login(owner_user, login):
    response = login(owner_user.email, "Password1")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'window.__APP_TOUR__ =' in html
    assert '"enabled": true' in html
    assert '"should_prompt": true' in html
    assert 'data-tour="tour-launcher"' in html


def test_staff_has_manual_tour_launcher_and_prompt(create_owner_user, login):
    staff_user = _create_staff_user(create_owner_user)
    response = login(staff_user.email, "Password1")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert '"enabled": true' in html
    assert '"role": "staff"' in html
    assert '"should_prompt": true' in html
    assert 'data-tour="tour-launcher"' in html


def test_super_admin_does_not_get_tour(create_super_admin_user, login):
    super_admin = create_super_admin_user(email="root-notour@example.com")

    response = login(super_admin.email, "Password1")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert '"role": "super_admin"' in html
    assert '"enabled": false' in html
    assert 'data-tour="tour-launcher"' not in html


def test_tour_dismiss_marks_current_version(owner_user, login, app, client):
    login(owner_user.email, "Password1")

    response = client.post("/tour/dismiss")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload == {"ok": True}

    refreshed = db.session.get(User, owner_user.id)
    assert refreshed.tour_dismissed_version == app.config["APP_TOUR_VERSION"]

    dashboard = client.get("/dashboard")
    assert dashboard.status_code == 200
    assert '"should_prompt": false' in dashboard.get_data(as_text=True)


def test_tour_complete_marks_current_version(owner_user, login, app, client):
    login(owner_user.email, "Password1")

    response = client.post("/tour/complete")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload == {"ok": True}

    refreshed = db.session.get(User, owner_user.id)
    assert refreshed.tour_completed_version == app.config["APP_TOUR_VERSION"]


def test_super_admin_cannot_update_tour_state(create_super_admin_user, login, client):
    super_admin = create_super_admin_user(email="root-tour-endpoint@example.com")
    login(super_admin.email, "Password1")

    dismiss_response = client.post("/tour/dismiss")
    complete_response = client.post("/tour/complete")

    assert dismiss_response.status_code == 403
    assert complete_response.status_code == 403
