"""Allow super admin without store

Revision ID: b8a3c2f7d4e1
Revises: 9f7c1d2b4a6e
Create Date: 2026-01-16 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "b8a3c2f7d4e1"
down_revision = "9f7c1d2b4a6e"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column(
            "store_id",
            existing_type=sa.Integer(),
            nullable=True,
        )


def downgrade():
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column(
            "store_id",
            existing_type=sa.Integer(),
            nullable=False,
        )
