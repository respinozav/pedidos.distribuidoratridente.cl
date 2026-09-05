"""Agrega campos de integracion Defontana a pedidos.

Revision ID: 20260905_0027
Revises: 20260903_0026
Create Date: 2026-09-05
"""

from alembic import op
from app.core.config import get_settings

revision = "20260905_0027"
down_revision = "20260903_0026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    schema = get_settings().database_schema
    op.execute(
        f"""
        ALTER TABLE {schema}.pedidos
        ADD COLUMN IF NOT EXISTS folio_defontana INTEGER,
        ADD COLUMN IF NOT EXISTS defontana_sincronizado BOOLEAN DEFAULT FALSE,
        ADD COLUMN IF NOT EXISTS defontana_error TEXT;
        """
    )


def downgrade() -> None:
    schema = get_settings().database_schema
    op.execute(
        f"""
        ALTER TABLE {schema}.pedidos
        DROP COLUMN IF EXISTS folio_defontana,
        DROP COLUMN IF EXISTS defontana_sincronizado,
        DROP COLUMN IF EXISTS defontana_error;
        """
    )
