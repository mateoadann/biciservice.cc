"""add bicycle brands table

Revision ID: a2b3c4d5e6f7
Revises: f3b2a1c4d5e6
Create Date: 2026-03-04 12:00:00.000000
"""

from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa

revision = "a2b3c4d5e6f7"
down_revision = "f3b2a1c4d5e6"
branch_labels = None
depends_on = None

PREDEFINED_BRANDS = [
    "BH", "BMC", "Cannodale", "Canyon", "Cervelo", "Cube", "Giant",
    "Marin", "Megamo", "Merida", "Orbea", "Otra", "Pinarello",
    "Santa Cruz", "Sava", "Scott", "Specialized", "Trek", "Vairo",
    "Venzo", "Volta",
]


def upgrade():
    # 1. Crear tabla bicycle_brands
    op.create_table(
        "bicycle_brands",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("workshop_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["workshop_id"], ["workshops.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workshop_id", "name", name="uq_bicycle_brand_workshop_name"),
    )
    op.create_index("ix_bicycle_brands_workshop_id", "bicycle_brands", ["workshop_id"])

    # 2. Poblar marcas predefinidas para cada workshop existente
    conn = op.get_bind()
    workshops = conn.execute(sa.text("SELECT id FROM workshops")).fetchall()
    now = datetime.now(timezone.utc)
    for (workshop_id,) in workshops:
        for brand_name in PREDEFINED_BRANDS:
            conn.execute(
                sa.text(
                    "INSERT INTO bicycle_brands (workshop_id, name, created_at) "
                    "VALUES (:wid, :name, :ts)"
                ),
                {"wid": workshop_id, "name": brand_name, "ts": now},
            )

    # 3. Agregar columna brand_id a bicycles (nullable)
    op.add_column("bicycles", sa.Column("brand_id", sa.Integer(), nullable=True))

    # 4. Migrar datos: vincular bicicletas existentes con sus marcas
    #    Para marcas que no existen en bicycle_brands, crearlas primero
    bicycles_with_brand = conn.execute(
        sa.text(
            "SELECT DISTINCT b.workshop_id, b.brand FROM bicycles b "
            "WHERE b.brand IS NOT NULL AND b.brand != ''"
        )
    ).fetchall()

    for workshop_id, brand_name in bicycles_with_brand:
        existing = conn.execute(
            sa.text(
                "SELECT id FROM bicycle_brands "
                "WHERE workshop_id = :wid AND name = :name"
            ),
            {"wid": workshop_id, "name": brand_name},
        ).fetchone()
        if not existing:
            conn.execute(
                sa.text(
                    "INSERT INTO bicycle_brands (workshop_id, name, created_at) "
                    "VALUES (:wid, :name, :ts)"
                ),
                {"wid": workshop_id, "name": brand_name, "ts": now},
            )

    # Ahora actualizar brand_id en bicycles
    conn.execute(
        sa.text(
            "UPDATE bicycles SET brand_id = ("
            "  SELECT bb.id FROM bicycle_brands bb "
            "  WHERE bb.workshop_id = bicycles.workshop_id "
            "  AND bb.name = bicycles.brand"
            ") WHERE brand IS NOT NULL AND brand != ''"
        )
    )

    # 5. Eliminar columna brand (el string viejo)
    op.drop_column("bicycles", "brand")

    # 6. Agregar FK constraint
    op.create_foreign_key(
        "fk_bicycles_brand_id",
        "bicycles",
        "bicycle_brands",
        ["brand_id"],
        ["id"],
    )


def downgrade():
    # 1. Eliminar FK constraint
    op.drop_constraint("fk_bicycles_brand_id", "bicycles", type_="foreignkey")

    # 2. Agregar columna brand string de vuelta
    op.add_column("bicycles", sa.Column("brand", sa.String(80), nullable=True))

    # 3. Migrar datos de vuelta: brand_id -> brand string
    conn = op.get_bind()
    conn.execute(
        sa.text(
            "UPDATE bicycles SET brand = ("
            "  SELECT bb.name FROM bicycle_brands bb "
            "  WHERE bb.id = bicycles.brand_id"
            ") WHERE brand_id IS NOT NULL"
        )
    )

    # 4. Eliminar columna brand_id
    op.drop_column("bicycles", "brand_id")

    # 5. Eliminar tabla bicycle_brands
    op.drop_index("ix_bicycle_brands_workshop_id", table_name="bicycle_brands")
    op.drop_table("bicycle_brands")
