"""Add workshop WhatsApp template

Revision ID: c17f2d4e8a9b
Revises: d9c6f1a4b2e7
Create Date: 2026-02-16 12:20:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "c17f2d4e8a9b"
down_revision = "d9c6f1a4b2e7"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("workshops", schema=None) as batch_op:
        batch_op.add_column(sa.Column("whatsapp_message_template", sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table("workshops", schema=None) as batch_op:
        batch_op.drop_column("whatsapp_message_template")
