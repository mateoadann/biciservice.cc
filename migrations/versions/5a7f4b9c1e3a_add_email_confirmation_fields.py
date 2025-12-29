"""add email confirmation fields

Revision ID: 5a7f4b9c1e3a
Revises: dc2b20e9bfc4
Create Date: 2026-01-05 10:12:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5a7f4b9c1e3a'
down_revision = 'dc2b20e9bfc4'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('email_confirmed', sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column('email_confirmed_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('confirmation_sent_at', sa.DateTime(), nullable=True))


def downgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('confirmation_sent_at')
        batch_op.drop_column('email_confirmed_at')
        batch_op.drop_column('email_confirmed')
