"""Agrega campos tiene_caja y cantidad_caja a tabla productos.

Revision ID: 20260901_0021
Revises: 20260826_0020
Create Date: 2026-09-01
"""

from alembic import op
import sqlalchemy as sa
from app.core.config import get_settings

revision = "20260901_0021"
down_revision = "20260826_0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    schema = get_settings().database_schema
    op.execute(
        f"""
        ALTER TABLE {schema}.productos
        ADD COLUMN IF NOT EXISTS tiene_caja BOOLEAN NOT NULL DEFAULT FALSE;

        ALTER TABLE {schema}.productos
        ADD COLUMN IF NOT EXISTS cantidad_caja INTEGER NULL;
        """
    )


def downgrade() -> None:
    schema = get_settings().database_schema
    op.execute(
        f"""
        ALTER TABLE {schema}.productos
        DROP COLUMN IF EXISTS cantidad_caja;

        ALTER TABLE {schema}.productos
        DROP COLUMN IF EXISTS tiene_caja;
        """
    )
