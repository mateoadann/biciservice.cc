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
    expected_cache_name = f"service-bicycle-static-{client.application.config['ASSET_VERSION']}"
    assert expected_cache_name in body
    expected_css_asset = f"/app.css?v={client.application.config['ASSET_VERSION']}"
    assert expected_css_asset in body


def test_apple_touch_icon_is_served(client):
    response = client.get("/apple-touch-icon.png")

    assert response.status_code == 200
    assert response.mimetype == "image/png"


def test_login_page_has_manifest_and_pwa_registration(client):
    response = client.get("/login")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    expected_version = client.application.config["ASSET_VERSION"]
    assert 'rel="manifest" href="/manifest.webmanifest"' in html
    assert f'window.__ASSET_VERSION__ = "{expected_version}"' in html
    assert f'/static/js/pwa-register.js?v={expected_version}' in html
    assert f'/app.css?v={expected_version}' in html


def test_dashboard_page_has_manifest_and_pwa_registration(owner_user, login, app):
    response = login(owner_user.email, "Password1")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    expected_version = app.config["ASSET_VERSION"]
    assert 'rel="manifest" href="/manifest.webmanifest"' in html
    assert f'window.__ASSET_VERSION__ = "{expected_version}"' in html
    assert f'/static/js/pwa-register.js?v={expected_version}' in html
    assert f'/app.css?v={expected_version}' in html


def test_app_css_is_served_with_no_store(client):
    response = client.get("/app.css")

    assert response.status_code == 200
    assert response.mimetype == "text/css"
    assert "no-store" in (response.headers.get("Cache-Control") or "")

    body = response.get_data(as_text=True)
    expected_version = client.application.config["ASSET_VERSION"]

    expected_imports = [
        "/static/css/base/fonts.css",
        "/static/css/base/tokens-reset.css",
        "/static/css/layout/shell.css",
        "/static/css/components/controls-core.css",
        "/static/css/components/flash.css",
        "/static/css/pages/dashboard-core.css",
        "/static/css/components/pagination.css",
        "/static/css/components/tables.css",
        "/static/css/components/status-chips-metrics.css",
        "/static/css/pages/dashboard-analytics.css",
        "/static/css/pages/settings.css",
        "/static/css/pages/jobs.css",
        "/static/css/components/modal.css",
        "/static/css/pages/settings-theme.css",
        "/static/css/pages/auth.css",
        "/static/css/base/accessibility-motion.css",
        "/static/css/layout/responsive.css",
    ]
    for path in expected_imports:
        assert f'{path}?v={expected_version}' in body
