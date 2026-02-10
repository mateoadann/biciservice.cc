def test_owner_dashboard_hides_global_audit_entry(client, owner_user, login):
    login(owner_user.email, "Password1")

    response = client.get("/dashboard")
    assert response.status_code == 200
    assert b"/audit" not in response.data
    assert b"Onboarding" in response.data


def test_owner_audit_route_redirects_to_dashboard(client, owner_user, login):
    login(owner_user.email, "Password1")

    response = client.get("/audit", follow_redirects=True)
    assert response.status_code == 200
    assert b"La auditoria global ya no esta disponible" in response.data
    assert b"Dashboard" in response.data
