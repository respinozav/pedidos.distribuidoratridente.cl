"""Agrega campos recibe_camila_whatsapp y recibe_camila_email a tabla usuarios.

Revision ID: 20261111_0039
Revises: 20261022_0038
Create Date: 2026-11-11
"""

from alembic import op
from app.core.config import get_settings

revision = "20261111_0039"
down_revision = "20261022_0038"
branch_labels = None
depends_on = None


def upgrade() -> None:
    schema = get_settings().database_schema
    op.execute(
        f"""
        ALTER TABLE {schema}.usuarios
        ADD COLUMN IF NOT EXISTS recibe_camila_whatsapp BOOLEAN NOT NULL DEFAULT false;
        """
    )
    op.execute(
        f"""
        ALTER TABLE {schema}.usuarios
        ADD COLUMN IF NOT EXISTS recibe_camila_email BOOLEAN NOT NULL DEFAULT false;
        """
    )


def downgrade() -> None:
    schema = get_settings().database_schema
    op.execute(
        f"""
        ALTER TABLE {schema}.usuarios
        DROP COLUMN IF EXISTS recibe_camila_whatsapp;
        """
    )
    op.execute(
        f"""
        ALTER TABLE {schema}.usuarios
        DROP COLUMN IF EXISTS recibe_camila_email;
        """
    )

