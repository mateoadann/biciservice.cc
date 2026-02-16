import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest
from sqlalchemy.pool import StaticPool

from app import create_app
from app.config import Config
from app.extensions import db
from app.models import Store, User, Workshop


class TestingConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False
    MAIL_SUPPRESS_SEND = True
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    SQLALCHEMY_ENGINE_OPTIONS = {
        "connect_args": {"check_same_thread": False},
        "poolclass": StaticPool,
    }
    UPLOAD_FOLDER = os.environ.get(
        "UPLOAD_FOLDER", str(Path("/tmp") / "service_bicycle_crm_test_uploads")
    )


@pytest.fixture
def app():
    app = create_app(TestingConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def create_owner_user(app):
    def _create(
        *,
        email="owner@example.com",
        full_name="Owner Test",
        password="Password1",
        email_confirmed=True,
        is_active=True,
        is_approved=True,
        workshop_name="Taller Test",
        store_name="Sucursal principal",
    ):
        workshop = Workshop()
        workshop.name = workshop_name
        db.session.add(workshop)
        db.session.flush()

        store = Store()
        store.name = store_name
        store.workshop_id = workshop.id
        db.session.add(store)
        db.session.flush()

        user = User()
        user.full_name = full_name
        user.email = email
        user.role = "owner"
        user.store_id = store.id
        user.email_confirmed = email_confirmed
        setattr(user, "is_active", is_active)
        user.is_approved = is_approved
        user.approved_at = datetime.now(timezone.utc) if is_approved else None
        user.set_password(password)
        user.workshops.append(workshop)
        db.session.add(user)
        db.session.commit()
        return user

    return _create


@pytest.fixture
def owner_user(create_owner_user):
    return create_owner_user()


@pytest.fixture
def create_super_admin_user(app):
    def _create(
        *,
        email="superadmin@example.com",
        full_name="Super Admin",
        password="Password1",
        is_active=True,
        is_approved=True,
    ):
        user = User()
        user.full_name = full_name
        user.email = email
        user.role = "super_admin"
        user.email_confirmed = True
        setattr(user, "is_active", is_active)
        user.is_approved = is_approved
        user.approved_at = datetime.now(timezone.utc) if is_approved else None
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return user

    return _create


@pytest.fixture
def login(client):
    def _login(email, password, *, follow_redirects=True):
        return client.post(
            "/login",
            data={"email": email, "password": password},
            follow_redirects=follow_redirects,
        )

    return _login
