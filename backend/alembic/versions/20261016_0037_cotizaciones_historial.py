"""Crea tablas cotizaciones_clientes y cotizaciones_productos para historial de cotizaciones.

Revision ID: 20261016_0037
Revises: 20261014_0036
Create Date: 2026-10-16
"""

from alembic import op
from app.core.config import get_settings

revision = "20261016_0037"
down_revision = "20261014_0036"
branch_labels = None
depends_on = None


def upgrade() -> None:
    schema = get_settings().database_schema
    try:
        op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")
    except Exception:
        pass

    # 1. Tabla cotizaciones_clientes
    op.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {schema}.cotizaciones_clientes (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            folio VARCHAR(50) UNIQUE NOT NULL,
            cliente_razon_social VARCHAR(255) NOT NULL,
            cliente_rut VARCHAR(20) NOT NULL,
            cliente_telefono VARCHAR(50) NOT NULL,
            cliente_correo VARCHAR(255) NOT NULL,
            cliente_direccion TEXT NOT NULL,
            cliente_comuna VARCHAR(100) DEFAULT '',
            cliente_observaciones TEXT DEFAULT '',
            fecha_emision TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            fecha_vencimiento TIMESTAMP WITH TIME ZONE NOT NULL,
            subtotal_neto NUMERIC(14, 2) DEFAULT 0,
            subtotal_exento NUMERIC(14, 2) DEFAULT 0,
            iva NUMERIC(14, 2) DEFAULT 0,
            total NUMERIC(14, 2) NOT NULL,
            total_items INTEGER DEFAULT 0,
            total_unidades INTEGER DEFAULT 0,
            productos JSONB NOT NULL DEFAULT '[]'::jsonb,
            estado VARCHAR(50) DEFAULT 'emitida',
            ip_origen VARCHAR(50),
            user_agent TEXT,
            usuario_id UUID REFERENCES {schema}.usuarios(id) ON DELETE SET NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        );
        """
    )

    # Si la tabla ya existía previamente en RDS, agregar columnas cliente_comuna y usuario_id
    op.execute(
        f"""
        ALTER TABLE {schema}.cotizaciones_clientes 
            ADD COLUMN IF NOT EXISTS cliente_comuna VARCHAR(100) DEFAULT '';
        """
    )
    op.execute(
        f"""
        ALTER TABLE {schema}.cotizaciones_clientes 
            ADD COLUMN IF NOT EXISTS usuario_id UUID REFERENCES {schema}.usuarios(id) ON DELETE SET NULL;
        """
    )

    # Índices cotizaciones_clientes
    op.execute(
        f"""
        CREATE INDEX IF NOT EXISTS idx_cotizaciones_clientes_rut 
            ON {schema}.cotizaciones_clientes(cliente_rut);
        """
    )
    op.execute(
        f"""
        CREATE INDEX IF NOT EXISTS idx_cotizaciones_clientes_folio 
            ON {schema}.cotizaciones_clientes(folio);
        """
    )
    op.execute(
        f"""
        CREATE INDEX IF NOT EXISTS idx_cotizaciones_clientes_fecha 
            ON {schema}.cotizaciones_clientes(fecha_emision DESC);
        """
    )

    # 2. Tabla cotizaciones_productos
    op.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {schema}.cotizaciones_productos (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            cotizacion_id UUID NOT NULL REFERENCES {schema}.cotizaciones_clientes(id) ON DELETE CASCADE,
            cotizacion_folio VARCHAR(50) NOT NULL,
            cliente_rut VARCHAR(20) NOT NULL,
            cliente_razon_social VARCHAR(255) NOT NULL,
            producto_id VARCHAR(100),
            codigo_sku VARCHAR(50),
            nombre_producto VARCHAR(255) NOT NULL,
            tipo_empaque VARCHAR(50) DEFAULT 'unidad',
            cantidad_caja INTEGER,
            precio_unitario NUMERIC(14, 2) NOT NULL,
            cantidad INTEGER NOT NULL DEFAULT 1,
            subtotal NUMERIC(14, 2) NOT NULL,
            afecto_iva BOOLEAN DEFAULT true,
            fecha_cotizacion TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        );
        """
    )

    # Índices cotizaciones_productos
    op.execute(
        f"""
        CREATE INDEX IF NOT EXISTS idx_cotizaciones_productos_cot_id 
            ON {schema}.cotizaciones_productos(cotizacion_id);
        """
    )
    op.execute(
        f"""
        CREATE INDEX IF NOT EXISTS idx_cotizaciones_productos_rut 
            ON {schema}.cotizaciones_productos(cliente_rut);
        """
    )
    op.execute(
        f"""
        CREATE INDEX IF NOT EXISTS idx_cotizaciones_productos_fecha 
            ON {schema}.cotizaciones_productos(fecha_cotizacion DESC);
        """
    )
    op.execute(
        f"""
        CREATE INDEX IF NOT EXISTS idx_cotizaciones_productos_sku 
            ON {schema}.cotizaciones_productos(codigo_sku);
        """
    )


def downgrade() -> None:
    schema = get_settings().database_schema
    op.execute(
        f"""
        DROP TABLE IF EXISTS {schema}.cotizaciones_productos;
        DROP TABLE IF EXISTS {schema}.cotizaciones_clientes;
        """
    )
