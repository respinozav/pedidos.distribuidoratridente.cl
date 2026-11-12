"""Crea tabla camila_logs para registrar conversaciones y ventas de Camila.

Revision ID: 20261112_0040
Revises: 20261111_0039
Create Date: 2026-11-12
"""

from alembic import op
from app.core.config import get_settings

revision = "20261112_0040"
down_revision = "20261111_0039"
branch_labels = None
depends_on = None


def upgrade() -> None:
    schema = get_settings().database_schema
    op.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {schema}.camila_logs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            razon_social VARCHAR(255) NOT NULL,
            whatsapp VARCHAR(50),
            correo VARCHAR(255),
            conversacion TEXT,
            resumen TEXT,
            total_estimado NUMERIC(12, 2),
            enviado_whatsapp BOOLEAN NOT NULL DEFAULT false,
            enviado_email BOOLEAN NOT NULL DEFAULT false,
            destinatarios_whatsapp TEXT,
            destinatarios_email TEXT,
            estado VARCHAR(50) NOT NULL DEFAULT 'COMPLETADA',
            origen VARCHAR(100) NOT NULL DEFAULT 'WEB_CAMILA',
            metadata_extra JSONB,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """
    )
    op.execute(
        f"""
        CREATE INDEX IF NOT EXISTS ix_camila_logs_created_at
        ON {schema}.camila_logs (created_at DESC);
        """
    )
    op.execute(
        f"""
        CREATE INDEX IF NOT EXISTS ix_camila_logs_razon_social
        ON {schema}.camila_logs (razon_social);
        """
    )
    op.execute(
        f"""
        CREATE INDEX IF NOT EXISTS ix_camila_logs_whatsapp
        ON {schema}.camila_logs (whatsapp);
        """
    )
    op.execute(
        f"""
        CREATE INDEX IF NOT EXISTS ix_camila_logs_correo
        ON {schema}.camila_logs (correo);
        """
    )
    op.execute(
        f"""
        CREATE INDEX IF NOT EXISTS ix_camila_logs_estado
        ON {schema}.camila_logs (estado);
        """
    )


def downgrade() -> None:
    schema = get_settings().database_schema
    op.execute(
        f"""
        DROP TABLE IF EXISTS {schema}.camila_logs CASCADE;
        """
    )
