"""Agrega tabla pedidos_voz y campo origen a pedidos.

Revision ID: 20261022_0039
Revises: 20261022_0038
Create Date: 2026-10-22
"""

from alembic import op
from app.core.config import get_settings

revision = "20261022_0039"
down_revision = "20261022_0038"
branch_labels = None
depends_on = None


def upgrade() -> None:
    schema = get_settings().database_schema
    # 1. Columna origen en pedidos
    op.execute(
        f"""
        ALTER TABLE {schema}.pedidos
        ADD COLUMN IF NOT EXISTS origen VARCHAR(30) DEFAULT 'web';
        """
    )
    op.execute(
        f"""
        CREATE INDEX IF NOT EXISTS ix_pedidos_origen ON {schema}.pedidos(origen);
        """
    )

    # 2. Tabla pedidos_voz para borradores, auditoría y respaldo de pedidos dictados
    op.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {schema}.pedidos_voz (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            usuario_id UUID NOT NULL REFERENCES {schema}.usuarios(id) ON DELETE RESTRICT,
            cliente_id UUID NULL REFERENCES {schema}.clientes(id) ON DELETE SET NULL,
            direccion_id UUID NULL REFERENCES {schema}.direcciones(id) ON DELETE SET NULL,
            pedido_id UUID NULL REFERENCES {schema}.pedidos(id) ON DELETE SET NULL UNIQUE,
            audio_url TEXT NULL,
            transcripcion TEXT NOT NULL,
            estado VARCHAR(30) NOT NULL DEFAULT 'BORRADOR',
            lineas_interpretadas JSONB NULL,
            lineas_editadas_count INT NOT NULL DEFAULT 0,
            total_estimado NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
            notas TEXT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """
    )
    op.execute(
        f"""
        CREATE INDEX IF NOT EXISTS ix_pedidos_voz_usuario_id ON {schema}.pedidos_voz(usuario_id);
        CREATE INDEX IF NOT EXISTS ix_pedidos_voz_cliente_id ON {schema}.pedidos_voz(cliente_id);
        CREATE INDEX IF NOT EXISTS ix_pedidos_voz_estado ON {schema}.pedidos_voz(estado);
        CREATE INDEX IF NOT EXISTS ix_pedidos_voz_created_at ON {schema}.pedidos_voz(created_at);
        """
    )


def downgrade() -> None:
    schema = get_settings().database_schema
    op.execute(
        f"""
        DROP TABLE IF EXISTS {schema}.pedidos_voz;
        """
    )
    op.execute(
        f"""
        DROP INDEX IF EXISTS {schema}.ix_pedidos_origen;
        ALTER TABLE {schema}.pedidos DROP COLUMN IF EXISTS origen;
        """
    )
