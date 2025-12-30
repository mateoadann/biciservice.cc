"""add job code

Revision ID: 7d2d2f4a9c31
Revises: 5a7f4b9c1e3a
Create Date: 2026-01-06 09:20:00.000000

"""
from alembic import op
import sqlalchemy as sa
import random
import string


# revision identifiers, used by Alembic.
revision = "7d2d2f4a9c31"
down_revision = "5a7f4b9c1e3a"
branch_labels = None
depends_on = None


def _generate_code(existing):
    alphabet = string.ascii_uppercase + string.digits
    while True:
        code = "".join(random.choices(alphabet, k=4))
        if code not in existing:
            existing.add(code)
            return code


def upgrade():
    with op.batch_alter_table("jobs", schema=None) as batch_op:
        batch_op.add_column(sa.Column("code", sa.String(length=4), nullable=True))

    connection = op.get_bind()
    result = connection.execute(sa.text("SELECT id FROM jobs"))
    existing = set()
    for row in result:
        code = _generate_code(existing)
        connection.execute(
            sa.text("UPDATE jobs SET code = :code WHERE id = :id"),
            {"code": code, "id": row.id},
        )

    with op.batch_alter_table("jobs", schema=None) as batch_op:
        batch_op.alter_column("code", nullable=False)
        batch_op.create_unique_constraint("uq_jobs_code", ["code"])


def downgrade():
    with op.batch_alter_table("jobs", schema=None) as batch_op:
        batch_op.drop_constraint("uq_jobs_code", type_="unique")
        batch_op.drop_column("code")
