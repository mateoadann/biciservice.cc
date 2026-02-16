from app.models import User
import app.services.email_service as email_service


def test_create_superadmin_command_creates_user(app):
    runner = app.test_cli_runner()

    result = runner.invoke(
        args=[
            "create-superadmin",
            "--email",
            "admin@example.com",
            "--name",
            "Admin Test",
            "--password",
            "Password1",
        ]
    )

    assert result.exit_code == 0
    assert "Super admin creado" in result.output

    user = User.query.filter_by(email="admin@example.com").first()
    assert user is not None
    assert user.role == "super_admin"
    assert user.is_approved is True


def test_create_superadmin_command_blocks_second_superadmin(app, create_super_admin_user):
    create_super_admin_user(email="existing-admin@example.com")
    runner = app.test_cli_runner()

    result = runner.invoke(
        args=[
            "create-superadmin",
            "--email",
            "new-admin@example.com",
            "--name",
            "Otro Admin",
            "--password",
            "Password1",
        ]
    )

    assert result.exit_code == 0
    assert "Ya existe un super admin" in result.output

    user = User.query.filter_by(email="new-admin@example.com").first()
    assert user is None


def test_send_test_email_command(app, monkeypatch):
    runner = app.test_cli_runner()
    called = {}

    def fake_send_email(to_email, subject, body):
        called["to"] = to_email
        called["subject"] = subject
        called["body"] = body
        return True

    monkeypatch.setattr(email_service, "send_email", fake_send_email)

    result = runner.invoke(
        args=[
            "send-test-email",
            "--to",
            "destino@example.com",
        ]
    )

    assert result.exit_code == 0
    assert "Correo de prueba enviado a destino@example.com" in result.output
    assert called["to"] == "destino@example.com"
    assert "Prueba de correo" in called["subject"]
