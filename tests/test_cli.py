from app.models import User


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
