"""Add user security fields

Revision ID: e1f9b3a7c2d4
Revises: c4f9b1a2d7c0
Create Date: 2026-01-18 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "e1f9b3a7c2d4"
down_revision = "c4f9b1a2d7c0"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "users",
        sa.Column(
            "failed_login_attempts",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.add_column("users", sa.Column("locked_until", sa.DateTime()))
    op.add_column(
        "users",
        sa.Column(
            "two_factor_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column("users", sa.Column("two_factor_secret", sa.String(length=32)))
    op.add_column(
        "users", sa.Column("password_reset_token_hash", sa.String(length=255))
    )
    op.add_column("users", sa.Column("password_reset_expires_at", sa.DateTime()))
    op.add_column("users", sa.Column("password_reset_sent_at", sa.DateTime()))


def downgrade():
    op.drop_column("users", "password_reset_sent_at")
    op.drop_column("users", "password_reset_expires_at")
    op.drop_column("users", "password_reset_token_hash")
    op.drop_column("users", "two_factor_secret")
    op.drop_column("users", "two_factor_enabled")
    op.drop_column("users", "locked_until")
    op.drop_column("users", "failed_login_attempts")
