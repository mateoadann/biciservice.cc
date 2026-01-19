"""Add job delivery date and parts

Revision ID: f2b3c4d5e6f7
Revises: e1f9b3a7c2d4
Create Date: 2026-01-18 13:30:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "f2b3c4d5e6f7"
down_revision = "e1f9b3a7c2d4"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("jobs", sa.Column("estimated_delivery_at", sa.Date(), nullable=True))
    op.execute(
        "UPDATE jobs SET estimated_delivery_at = DATE(created_at) "
        "WHERE estimated_delivery_at IS NULL"
    )
    op.alter_column("jobs", "estimated_delivery_at", nullable=False)

    op.create_table(
        "job_parts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("job_id", sa.Integer(), sa.ForeignKey("jobs.id"), nullable=False),
        sa.Column("description", sa.String(length=200), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("unit_price", sa.Numeric(10, 2), nullable=False, server_default=sa.text("0")),
        sa.Column("kind", sa.String(length=20), nullable=False, server_default=sa.text("'part'")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )


def downgrade():
    op.drop_table("job_parts")
    op.drop_column("jobs", "estimated_delivery_at")
