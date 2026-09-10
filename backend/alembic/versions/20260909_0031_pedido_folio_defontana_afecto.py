"""Agrega campo folio_defontana_afecto a tabla pedidos.

Revision ID: 20260909_0031
Revises: 20260909_0030
Create Date: 2026-09-09
"""

from alembic import op
from app.core.config import get_settings

revision = "20260909_0031"
down_revision = "20260909_0030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    schema = get_settings().database_schema
    op.execute(
        f"""
        ALTER TABLE {schema}.pedidos
        ADD COLUMN IF NOT EXISTS folio_defontana_afecto INTEGER;

        CREATE INDEX IF NOT EXISTS ix_pedidos_folio_defontana_afecto
        ON {schema}.pedidos (folio_defontana_afecto);
        """
    )


def downgrade() -> None:
    schema = get_settings().database_schema
    op.execute(
        f"""
        DROP INDEX IF EXISTS {schema}.ix_pedidos_folio_defontana_afecto;

        ALTER TABLE {schema}.pedidos
        DROP COLUMN IF EXISTS folio_defontana_afecto;
        """
    )
