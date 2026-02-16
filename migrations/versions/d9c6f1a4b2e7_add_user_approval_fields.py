"""Add user approval fields

Revision ID: d9c6f1a4b2e7
Revises: a1b2c3d4e5f6
Create Date: 2026-02-15 10:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "d9c6f1a4b2e7"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(sa.Column("is_approved", sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column("approved_at", sa.DateTime(), nullable=True))

    op.execute("UPDATE users SET is_approved = true WHERE is_approved IS NULL")

    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.alter_column(
            "is_approved",
            existing_type=sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        )


def downgrade():
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("approved_at")
        batch_op.drop_column("is_approved")
