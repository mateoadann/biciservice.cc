"""shift audit logs to cordoba local time

Revision ID: e7a1c9d2b3f4
Revises: f8c1e2a4b9d0
Create Date: 2026-02-28 18:20:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "e7a1c9d2b3f4"
down_revision = "f8c1e2a4b9d0"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            sa.text(
                """
                UPDATE audit_logs
                SET created_at = created_at - INTERVAL '3 hours'
                WHERE created_at IS NOT NULL
                """
            )
        )
        return

    op.execute(
        sa.text(
            """
            UPDATE audit_logs
            SET created_at = datetime(created_at, '-3 hours')
            WHERE created_at IS NOT NULL
            """
        )
    )


def downgrade():
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            sa.text(
                """
                UPDATE audit_logs
                SET created_at = created_at + INTERVAL '3 hours'
                WHERE created_at IS NOT NULL
                """
            )
        )
        return

    op.execute(
        sa.text(
            """
            UPDATE audit_logs
            SET created_at = datetime(created_at, '+3 hours')
            WHERE created_at IS NOT NULL
            """
        )
    )
