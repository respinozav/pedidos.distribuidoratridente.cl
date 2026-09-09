"""Crea tablas carritos_compras y carritos_compras_items y agrega carro_compras_expira_horas a system_settings.

Revision ID: 20260908_0028
Revises: 20260905_0027
Create Date: 2026-09-08
"""

from alembic import op
from app.core.config import get_settings

revision = "20260908_0028"
down_revision = "20260905_0027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    schema = get_settings().database_schema

    # 1. Agregar carro_compras_expira_horas a system_settings
    op.execute(
        f"""
        ALTER TABLE {schema}.system_settings
        ADD COLUMN IF NOT EXISTS carro_compras_expira_horas INTEGER DEFAULT 24;
        """
    )

    # 2. Crear tabla carritos_compras
    op.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {schema}.carritos_compras (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            cliente_id UUID NOT NULL REFERENCES {schema}.clientes(id) ON DELETE CASCADE,
            direccion_id UUID REFERENCES {schema}.direcciones(id) ON DELETE SET NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            CONSTRAINT uq_carritos_compras_cliente UNIQUE (cliente_id)
        );
        CREATE INDEX IF NOT EXISTS ix_carritos_compras_cliente_id ON {schema}.carritos_compras(cliente_id);
        CREATE INDEX IF NOT EXISTS ix_carritos_compras_updated_at ON {schema}.carritos_compras(updated_at);
        """
    )

    # 3. Crear tabla carritos_compras_items
    op.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {schema}.carritos_compras_items (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            carrito_id UUID NOT NULL REFERENCES {schema}.carritos_compras(id) ON DELETE CASCADE,
            producto_id UUID NOT NULL REFERENCES {schema}.productos(id) ON DELETE RESTRICT,
            cantidad INTEGER NOT NULL CHECK (cantidad > 0),
            tipo_empaque VARCHAR(20) NOT NULL DEFAULT 'unidad',
            cantidad_caja INTEGER NULL,
            precio_unitario NUMERIC(12, 2) NOT NULL DEFAULT 0,
            subtotal NUMERIC(12, 2) NOT NULL DEFAULT 0,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            CONSTRAINT uq_carritos_compras_items_line UNIQUE (carrito_id, producto_id, tipo_empaque)
        );
        CREATE INDEX IF NOT EXISTS ix_carritos_compras_items_carrito_id ON {schema}.carritos_compras_items(carrito_id);
        CREATE INDEX IF NOT EXISTS ix_carritos_compras_items_producto_id ON {schema}.carritos_compras_items(producto_id);
        """
    )


def downgrade() -> None:
    schema = get_settings().database_schema

    op.execute(f"DROP TABLE IF EXISTS {schema}.carritos_compras_items CASCADE;")
    op.execute(f"DROP TABLE IF EXISTS {schema}.carritos_compras CASCADE;")
    op.execute(
        f"""
        ALTER TABLE {schema}.system_settings
        DROP COLUMN IF EXISTS carro_compras_expira_horas;
        """
    )
