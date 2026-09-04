"""Agrega timezone a system_settings.

Revision ID: 20260903_0026
Revises: 20260902_0025
Create Date: 2026-09-03
"""

from alembic import op
from app.core.config import get_settings

revision = "20260903_0026"
down_revision = "20260902_0025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    schema = get_settings().database_schema
    op.execute(
        f"""
        ALTER TABLE {schema}.system_settings
        ADD COLUMN IF NOT EXISTS timezone VARCHAR(100) DEFAULT 'America/Santiago';
        """
    )


def downgrade() -> None:
    schema = get_settings().database_schema
    op.execute(
        f"""
        ALTER TABLE {schema}.system_settings
        DROP COLUMN IF EXISTS timezone;
        """
    )
