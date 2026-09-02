"""Agrega campo dias_credito a tabla clientes.

Revision ID: 20260902_0024
Revises: 20260901_0023
Create Date: 2026-09-02
"""

from alembic import op
import sqlalchemy as sa
from app.core.config import get_settings

revision = "20260902_0024"
down_revision = "20260901_0023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    schema = get_settings().database_schema
    op.execute(
        f"""
        ALTER TABLE {schema}.clientes
        ADD COLUMN IF NOT EXISTS dias_credito INTEGER DEFAULT 0 NOT NULL;
        """
    )


def downgrade() -> None:
    schema = get_settings().database_schema
    op.execute(
        f"""
        ALTER TABLE {schema}.clientes
        DROP COLUMN IF EXISTS dias_credito;
        """
    )
