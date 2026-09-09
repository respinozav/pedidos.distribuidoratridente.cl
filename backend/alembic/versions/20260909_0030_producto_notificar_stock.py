"""Agrega campos notificar_stock y stock_notificacion a tabla productos.

Revision ID: 20260909_0030
Revises: 20260909_0029
Create Date: 2026-09-09
"""

from alembic import op
from app.core.config import get_settings

revision = "20260909_0030"
down_revision = "20260909_0029"
branch_labels = None
depends_on = None


def upgrade() -> None:
    schema = get_settings().database_schema
    op.execute(
        f"""
        ALTER TABLE {schema}.productos
        ADD COLUMN IF NOT EXISTS notificar_stock BOOLEAN NOT NULL DEFAULT FALSE;

        ALTER TABLE {schema}.productos
        ADD COLUMN IF NOT EXISTS stock_notificacion INTEGER NULL;
        """
    )


def downgrade() -> None:
    schema = get_settings().database_schema
    op.execute(
        f"""
        ALTER TABLE {schema}.productos
        DROP COLUMN IF EXISTS stock_notificacion;

        ALTER TABLE {schema}.productos
        DROP COLUMN IF EXISTS notificar_stock;
        """
    )
