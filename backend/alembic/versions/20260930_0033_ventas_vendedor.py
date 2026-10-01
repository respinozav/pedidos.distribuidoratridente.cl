"""Crea tabla ventas_vendedor, detalles_ventas_vendedor y agrega vendedor_id a pedidos.

Revision ID: 20260930_0033
Revises: 20260930_0032
Create Date: 2026-09-30
"""

from alembic import op
from app.core.config import get_settings

revision = "20260930_0033"
down_revision = "20260930_0032"
branch_labels = None
depends_on = None


def upgrade() -> None:
    schema = get_settings().database_schema
    op.execute(
        f"""
        ALTER TABLE {schema}.pedidos
        ADD COLUMN IF NOT EXISTS vendedor_id UUID REFERENCES {schema}.usuarios(id);

        CREATE INDEX IF NOT EXISTS ix_pedidos_vendedor_id ON {schema}.pedidos(vendedor_id);

        CREATE TABLE IF NOT EXISTS {schema}.ventas_vendedor (
            id UUID PRIMARY KEY,
            vendedor_id UUID NOT NULL REFERENCES {schema}.usuarios(id),
            pedido_id UUID NOT NULL REFERENCES {schema}.pedidos(id) UNIQUE,
            cliente_id UUID NOT NULL REFERENCES {schema}.clientes(id),
            total_venta NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
            comision_total NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        );

        CREATE INDEX IF NOT EXISTS ix_ventas_vendedor_vendedor_id ON {schema}.ventas_vendedor(vendedor_id);
        CREATE INDEX IF NOT EXISTS ix_ventas_vendedor_cliente_id ON {schema}.ventas_vendedor(cliente_id);
        CREATE INDEX IF NOT EXISTS ix_ventas_vendedor_pedido_id ON {schema}.ventas_vendedor(pedido_id);

        CREATE TABLE IF NOT EXISTS {schema}.detalles_ventas_vendedor (
            id UUID PRIMARY KEY,
            venta_vendedor_id UUID NOT NULL REFERENCES {schema}.ventas_vendedor(id) ON DELETE CASCADE,
            producto_id UUID REFERENCES {schema}.productos(id),
            categoria_id UUID REFERENCES {schema}.categorias(id),
            nombre_producto VARCHAR(180) NOT NULL,
            nombre_categoria VARCHAR(120),
            cantidad INTEGER NOT NULL DEFAULT 1,
            precio_unitario NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
            subtotal NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
            comision_porcentaje NUMERIC(5, 2) NOT NULL DEFAULT 0.00,
            comision_monto NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        );

        CREATE INDEX IF NOT EXISTS ix_detalles_ventas_vendedor_venta_id ON {schema}.detalles_ventas_vendedor(venta_vendedor_id);
        """
    )


def downgrade() -> None:
    schema = get_settings().database_schema
    op.execute(
        f"""
        DROP TABLE IF EXISTS {schema}.detalles_ventas_vendedor;
        DROP TABLE IF EXISTS {schema}.ventas_vendedor;
        DROP INDEX IF EXISTS {schema}.ix_pedidos_vendedor_id;
        ALTER TABLE {schema}.pedidos DROP COLUMN IF EXISTS vendedor_id;
        """
    )
