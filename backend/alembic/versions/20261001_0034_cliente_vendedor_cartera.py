"""Agrega vendedor_id a clientes para asignacion de cartera.

Revision ID: 20261001_0034
Revises: 20260930_0033
Create Date: 2026-10-01
"""

from alembic import op
from app.core.config import get_settings

revision = "20261001_0034"
down_revision = "20260930_0033"
branch_labels = None
depends_on = None


def upgrade() -> None:
    schema = get_settings().database_schema
    op.execute(
        f"""
        ALTER TABLE {schema}.clientes
        ADD COLUMN IF NOT EXISTS vendedor_id UUID REFERENCES {schema}.usuarios(id);

        CREATE INDEX IF NOT EXISTS ix_clientes_vendedor_id ON {schema}.clientes(vendedor_id);
        """
    )


def downgrade() -> None:
    schema = get_settings().database_schema
    op.execute(
        f"""
        DROP INDEX IF EXISTS {schema}.ix_clientes_vendedor_id;
        ALTER TABLE {schema}.clientes DROP COLUMN IF EXISTS vendedor_id;
        """
    )
