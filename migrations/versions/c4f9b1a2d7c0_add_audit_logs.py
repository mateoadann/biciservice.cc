"""Add audit logs

Revision ID: c4f9b1a2d7c0
Revises: b8a3c2f7d4e1
Create Date: 2026-01-16 12:30:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "c4f9b1a2d7c0"
down_revision = "b8a3c2f7d4e1"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("workshop_id", sa.Integer(), sa.ForeignKey("workshops.id")),
        sa.Column("store_id", sa.Integer(), sa.ForeignKey("stores.id")),
        sa.Column("action", sa.String(length=40), nullable=False),
        sa.Column("entity_type", sa.String(length=40), nullable=False),
        sa.Column("entity_id", sa.Integer()),
        sa.Column("description", sa.Text()),
        sa.Column("ip_address", sa.String(length=45)),
        sa.Column("user_agent", sa.String(length=255)),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )


def downgrade():
    op.drop_table("audit_logs")
