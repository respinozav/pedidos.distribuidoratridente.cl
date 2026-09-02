"""Agrega campo precio_caja a tabla productos.

Revision ID: 20260901_0022
Revises: 20260901_0021
Create Date: 2026-09-01
"""

from alembic import op
import sqlalchemy as sa
from app.core.config import get_settings

revision = "20260901_0022"
down_revision = "20260901_0021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    schema = get_settings().database_schema
    op.execute(
        f"""
        ALTER TABLE {schema}.productos
        ADD COLUMN IF NOT EXISTS precio_caja NUMERIC(12, 2) NULL;
        """
    )


def downgrade() -> None:
    schema = get_settings().database_schema
    op.execute(
        f"""
        ALTER TABLE {schema}.productos
        DROP COLUMN IF EXISTS precio_caja;
        """
    )
