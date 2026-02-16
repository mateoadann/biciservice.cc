def test_manifest_is_served(client):
    response = client.get("/manifest.webmanifest")

    assert response.status_code == 200
    assert response.headers.get("Cache-Control") == "no-cache"

    payload = response.get_json()
    assert payload is not None
    assert payload.get("display") == "standalone"
    assert payload.get("start_url") == "/login"

    icons = payload.get("icons", [])
    icon_paths = {icon.get("src") for icon in icons}
    assert "/static/icons/pwa-192.png" in icon_paths
    assert "/static/icons/pwa-512.png" in icon_paths


def test_service_worker_is_served_with_no_store(client):
    response = client.get("/sw.js")

    assert response.status_code == 200
    assert "no-store" in (response.headers.get("Cache-Control") or "")

    body = response.get_data(as_text=True)
    assert "CACHE_NAME_STATIC" in body
    assert "SENSITIVE_PREFIXES" in body


def test_apple_touch_icon_is_served(client):
    response = client.get("/apple-touch-icon.png")

    assert response.status_code == 200
    assert response.mimetype == "image/png"


def test_login_page_has_manifest_and_pwa_registration(client):
    response = client.get("/login")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'rel="manifest" href="/manifest.webmanifest"' in html
    assert '/static/js/pwa-register.js' in html


def test_dashboard_page_has_manifest_and_pwa_registration(owner_user, login):
    response = login(owner_user.email, "Password1")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'rel="manifest" href="/manifest.webmanifest"' in html
    assert '/static/js/pwa-register.js' in html
