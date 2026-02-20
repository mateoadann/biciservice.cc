"""add performance indexes

Revision ID: f8c1e2a4b9d0
Revises: c17f2d4e8a9b
Create Date: 2026-02-18 00:00:00.000000
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "f8c1e2a4b9d0"
down_revision = "c17f2d4e8a9b"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("clients", schema=None) as batch_op:
        batch_op.create_index("ix_clients_workshop_id", ["workshop_id"], unique=False)

    with op.batch_alter_table("stores", schema=None) as batch_op:
        batch_op.create_index("ix_stores_workshop_id", ["workshop_id"], unique=False)

    with op.batch_alter_table("bicycles", schema=None) as batch_op:
        batch_op.create_index("ix_bicycles_workshop_id", ["workshop_id"], unique=False)
        batch_op.create_index("ix_bicycles_client_id", ["client_id"], unique=False)

    with op.batch_alter_table("service_types", schema=None) as batch_op:
        batch_op.create_index(
            "ix_service_types_workshop_id", ["workshop_id"], unique=False
        )

    with op.batch_alter_table("jobs", schema=None) as batch_op:
        batch_op.create_index(
            "ix_jobs_workshop_store_status",
            ["workshop_id", "store_id", "status"],
            unique=False,
        )
        batch_op.create_index(
            "ix_jobs_estimated_delivery", ["estimated_delivery_at"], unique=False
        )

    with op.batch_alter_table("audit_logs", schema=None) as batch_op:
        batch_op.create_index(
            "ix_audit_entity", ["entity_type", "entity_id", "action"], unique=False
        )

    with op.batch_alter_table("job_parts", schema=None) as batch_op:
        batch_op.create_index("ix_job_parts_job_id", ["job_id"], unique=False)

    with op.batch_alter_table("job_items", schema=None) as batch_op:
        batch_op.create_index("ix_job_items_job_id", ["job_id"], unique=False)


def downgrade():
    with op.batch_alter_table("job_items", schema=None) as batch_op:
        batch_op.drop_index("ix_job_items_job_id")

    with op.batch_alter_table("job_parts", schema=None) as batch_op:
        batch_op.drop_index("ix_job_parts_job_id")

    with op.batch_alter_table("audit_logs", schema=None) as batch_op:
        batch_op.drop_index("ix_audit_entity")

    with op.batch_alter_table("jobs", schema=None) as batch_op:
        batch_op.drop_index("ix_jobs_estimated_delivery")
        batch_op.drop_index("ix_jobs_workshop_store_status")

    with op.batch_alter_table("service_types", schema=None) as batch_op:
        batch_op.drop_index("ix_service_types_workshop_id")

    with op.batch_alter_table("bicycles", schema=None) as batch_op:
        batch_op.drop_index("ix_bicycles_client_id")
        batch_op.drop_index("ix_bicycles_workshop_id")

    with op.batch_alter_table("stores", schema=None) as batch_op:
        batch_op.drop_index("ix_stores_workshop_id")

    with op.batch_alter_table("clients", schema=None) as batch_op:
        batch_op.drop_index("ix_clients_workshop_id")
