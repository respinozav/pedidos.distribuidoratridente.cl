"""Crea tabla sesion_logs para registrar auditoria de inicios de sesion de administradores y clientes.

Revision ID: 20260826_0020
Revises: 20260826_0019
Create Date: 2026-08-26
"""

from alembic import op
import sqlalchemy as sa
from app.core.config import get_settings

revision = "20260826_0020"
down_revision = "20260826_0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    schema = get_settings().database_schema
    op.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {schema}.sesion_logs (
            id UUID PRIMARY KEY,
            tipo_usuario VARCHAR(30) NOT NULL,
            usuario_id UUID REFERENCES {schema}.usuarios(id) ON DELETE SET NULL,
            cliente_id UUID REFERENCES {schema}.clientes(id) ON DELETE SET NULL,
            correo VARCHAR(255) NOT NULL,
            nombre VARCHAR(255),
            estado VARCHAR(30) NOT NULL,
            mensaje VARCHAR(255),
            ip_address VARCHAR(100),
            user_agent TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        CREATE INDEX IF NOT EXISTS ix_sesion_logs_tipo_usuario_estado
            ON {schema}.sesion_logs (tipo_usuario, estado);

        CREATE INDEX IF NOT EXISTS ix_sesion_logs_correo
            ON {schema}.sesion_logs (correo);

        CREATE INDEX IF NOT EXISTS ix_sesion_logs_created_at
            ON {schema}.sesion_logs (created_at DESC);
        """
    )


def downgrade() -> None:
    schema = get_settings().database_schema
    op.execute(f"DROP TABLE IF EXISTS {schema}.sesion_logs CASCADE;")
