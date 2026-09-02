"""Agrega campos tipo_empaque y cantidad_caja a tabla detalle_pedidos.

Revision ID: 20260901_0023
Revises: 20260901_0022
Create Date: 2026-09-01
"""

from alembic import op
import sqlalchemy as sa
from app.core.config import get_settings

revision = "20260901_0023"
down_revision = "20260901_0022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    schema = get_settings().database_schema
    op.execute(
        f"""
        ALTER TABLE {schema}.detalle_pedidos
        ADD COLUMN IF NOT EXISTS tipo_empaque VARCHAR(20) DEFAULT 'unidad' NOT NULL,
        ADD COLUMN IF NOT EXISTS cantidad_caja INTEGER NULL;
        """
    )


def downgrade() -> None:
    schema = get_settings().database_schema
    op.execute(
        f"""
        ALTER TABLE {schema}.detalle_pedidos
        DROP COLUMN IF EXISTS tipo_empaque,
        DROP COLUMN IF EXISTS cantidad_caja;
        """
    )
