"""add user tour tracking fields

Revision ID: f3b2a1c4d5e6
Revises: e7a1c9d2b3f4
Create Date: 2026-02-28 20:25:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "f3b2a1c4d5e6"
down_revision = "e7a1c9d2b3f4"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(sa.Column("tour_completed_version", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("tour_dismissed_version", sa.Integer(), nullable=True))

    op.execute(
        sa.text(
            """
            UPDATE users
            SET tour_completed_version = 0,
                tour_dismissed_version = 0
            WHERE tour_completed_version IS NULL OR tour_dismissed_version IS NULL
            """
        )
    )

    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.alter_column(
            "tour_completed_version",
            existing_type=sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        )
        batch_op.alter_column(
            "tour_dismissed_version",
            existing_type=sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        )


def downgrade():
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("tour_dismissed_version")
        batch_op.drop_column("tour_completed_version")
