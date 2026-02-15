"""add client_code

Revision ID: a1b2c3d4e5f6
Revises: f2b3c4d5e6f7
Create Date: 2026-02-13

"""
from alembic import op
import sqlalchemy as sa

revision = "a1b2c3d4e5f6"
down_revision = "f2b3c4d5e6f7"
branch_labels = None
depends_on = None


def upgrade():
    # Step 1: Add column as nullable
    op.add_column("clients", sa.Column("client_code", sa.String(10), nullable=True))

    # Step 2: Backfill existing clients with sequential codes per workshop
    conn = op.get_bind()
    workshops = conn.execute(
        sa.text("SELECT DISTINCT workshop_id FROM clients")
    ).fetchall()
    for (workshop_id,) in workshops:
        clients = conn.execute(
            sa.text(
                "SELECT id FROM clients WHERE workshop_id = :wid ORDER BY id"
            ),
            {"wid": workshop_id},
        ).fetchall()
        for idx, (client_id,) in enumerate(clients):
            code = str(100 + idx)
            conn.execute(
                sa.text("UPDATE clients SET client_code = :code WHERE id = :cid"),
                {"code": code, "cid": client_id},
            )

    # Step 3: Make non-nullable
    op.alter_column("clients", "client_code", nullable=False)

    # Step 4: Add unique constraint
    op.create_unique_constraint(
        "uq_client_workshop_code", "clients", ["workshop_id", "client_code"]
    )


def downgrade():
    op.drop_constraint("uq_client_workshop_code", "clients", type_="unique")
    op.drop_column("clients", "client_code")
