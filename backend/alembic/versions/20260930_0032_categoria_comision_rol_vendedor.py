"""Agrega comision_porcentaje a categorias y crea el rol VENDEDOR.

Revision ID: 20260930_0032
Revises: 20260909_0031
Create Date: 2026-09-30
"""

from uuid import uuid4
from alembic import op
from sqlalchemy import text
from app.core.config import get_settings

revision = "20260930_0032"
down_revision = "20260909_0031"
branch_labels = None
depends_on = None


def upgrade() -> None:
    schema = get_settings().database_schema
    new_id = str(uuid4())
    op.execute(
        f"""
        ALTER TABLE {schema}.categorias
        ADD COLUMN IF NOT EXISTS comision_porcentaje NUMERIC(5, 2) NOT NULL DEFAULT 0.00;

        INSERT INTO {schema}.roles (id, nombre, activo, created_at, updated_at)
        SELECT '{new_id}'::uuid, 'VENDEDOR', true, NOW(), NOW()
        WHERE NOT EXISTS (
            SELECT 1 FROM {schema}.roles WHERE UPPER(nombre) = 'VENDEDOR'
        );
        """
    )


def downgrade() -> None:
    schema = get_settings().database_schema
    op.execute(
        f"""
        ALTER TABLE {schema}.categorias
        DROP COLUMN IF EXISTS comision_porcentaje;
        """
    )
