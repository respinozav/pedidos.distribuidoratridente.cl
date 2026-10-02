"""Crea tabla avisos_stock_cliente para notificaciones de reposicion.

Revision ID: 20261001_0035
Revises: 20261001_0034
Create Date: 2026-10-01
"""

from alembic import op
from app.core.config import get_settings

revision = "20261001_0035"
down_revision = "20261001_0034"
branch_labels = None
depends_on = None


def upgrade() -> None:
    schema = get_settings().database_schema
    op.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {schema}.avisos_stock_cliente (
            id UUID PRIMARY KEY,
            cliente_id UUID NOT NULL REFERENCES {schema}.clientes(id) ON DELETE CASCADE,
            producto_id UUID NOT NULL REFERENCES {schema}.productos(id) ON DELETE CASCADE,
            correo VARCHAR(255) NOT NULL,
            estado VARCHAR(30) NOT NULL DEFAULT 'PENDIENTE',
            notificado_at TIMESTAMP WITH TIME ZONE NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        );

        CREATE INDEX IF NOT EXISTS ix_avisos_stock_cliente_producto_estado 
            ON {schema}.avisos_stock_cliente(producto_id, estado);
        CREATE INDEX IF NOT EXISTS ix_avisos_stock_cliente_cliente_id 
            ON {schema}.avisos_stock_cliente(cliente_id);
        CREATE INDEX IF NOT EXISTS ix_avisos_stock_cliente_estado 
            ON {schema}.avisos_stock_cliente(estado);
        """
    )


def downgrade() -> None:
    schema = get_settings().database_schema
    op.execute(
        f"""
        DROP TABLE IF EXISTS {schema}.avisos_stock_cliente;
        """
    )
