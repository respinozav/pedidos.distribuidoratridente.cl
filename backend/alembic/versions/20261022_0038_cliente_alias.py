"""Agrega campo alias a tabla clientes.

Revision ID: 20261022_0038
Revises: 20261016_0037
Create Date: 2026-10-22
"""

from alembic import op
from app.core.config import get_settings

revision = "20261022_0038"
down_revision = "20261016_0037"
branch_labels = None
depends_on = None


def upgrade() -> None:
    schema = get_settings().database_schema
    op.execute(
        f"""
        ALTER TABLE {schema}.clientes
        ADD COLUMN IF NOT EXISTS alias VARCHAR(180) NULL;
        """
    )
    op.execute(
        f"""
        CREATE INDEX IF NOT EXISTS ix_clientes_alias ON {schema}.clientes(alias);
        """
    )


def downgrade() -> None:
    schema = get_settings().database_schema
    op.execute(
        f"""
        DROP INDEX IF EXISTS {schema}.ix_clientes_alias;
        """
    )
    op.execute(
        f"""
        ALTER TABLE {schema}.clientes
        DROP COLUMN IF EXISTS alias;
        """
    )
