"""add stores and roles

Revision ID: 9f7c1d2b4a6e
Revises: 7d2d2f4a9c31
Create Date: 2026-01-15 18:10:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "9f7c1d2b4a6e"
down_revision = "7d2d2f4a9c31"
branch_labels = None
depends_on = None


DEFAULT_STORE_NAME = "Sucursal principal"


def upgrade():
    op.create_table(
        "stores",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("workshop_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["workshop_id"], ["workshops.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("role", sa.String(length=20), server_default="owner", nullable=False)
        )
        batch_op.add_column(sa.Column("store_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key("fk_users_store_id", "stores", ["store_id"], ["id"])

    with op.batch_alter_table("jobs", schema=None) as batch_op:
        batch_op.add_column(sa.Column("store_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key("fk_jobs_store_id", "stores", ["store_id"], ["id"])

    connection = op.get_bind()
    workshops = connection.execute(sa.text("SELECT id FROM workshops")).fetchall()
    store_map = {}

    for row in workshops:
        result = connection.execute(
            sa.text(
                "INSERT INTO stores (workshop_id, name, created_at) "
                "VALUES (:workshop_id, :name, NOW()) RETURNING id"
            ),
            {"workshop_id": row.id, "name": DEFAULT_STORE_NAME},
        ).fetchone()
        store_map[row.id] = result.id

    for workshop_id, store_id in store_map.items():
        connection.execute(
            sa.text(
                "UPDATE users SET role = 'owner', store_id = :store_id "
                "WHERE id IN (SELECT user_id FROM user_workshops WHERE workshop_id = :workshop_id)"
            ),
            {"store_id": store_id, "workshop_id": workshop_id},
        )
        connection.execute(
            sa.text(
                "UPDATE jobs SET store_id = :store_id WHERE workshop_id = :workshop_id"
            ),
            {"store_id": store_id, "workshop_id": workshop_id},
        )

    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.alter_column("store_id", nullable=False)

    with op.batch_alter_table("jobs", schema=None) as batch_op:
        batch_op.alter_column("store_id", nullable=False)


def downgrade():
    with op.batch_alter_table("jobs", schema=None) as batch_op:
        batch_op.drop_constraint("fk_jobs_store_id", type_="foreignkey")
        batch_op.drop_column("store_id")

    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_constraint("fk_users_store_id", type_="foreignkey")
        batch_op.drop_column("store_id")
        batch_op.drop_column("role")

    op.drop_table("stores")
