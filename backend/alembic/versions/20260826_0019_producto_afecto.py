"""Agrega campo afecto a tabla productos y marca categorias especificas como afecto.

Revision ID: 20260826_0019
Revises: 20260823_0018
Create Date: 2026-08-26
"""

from alembic import op
import sqlalchemy as sa
from app.core.config import get_settings

revision = "20260826_0019"
down_revision = "20260823_0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    schema = get_settings().database_schema
    op.execute(
        f"""
        ALTER TABLE {schema}.productos
        ADD COLUMN IF NOT EXISTS afecto BOOLEAN NOT NULL DEFAULT FALSE;

        UPDATE {schema}.productos
        SET afecto = TRUE
        WHERE categoria_id IN (
            '55adf0bc-8f84-46b8-b693-a8948af9b18c',
            'f01a1b57-9a2b-4dbd-9011-87b05f56041d',
            'ad15aaf0-6e14-4365-99cf-3c47c00cfcf9',
            '724cb8de-993b-4ba4-ab30-774f61d3edc8'
        );
        """
    )


def downgrade() -> None:
    schema = get_settings().database_schema
    op.execute(
        f"""
        ALTER TABLE {schema}.productos
        DROP COLUMN IF EXISTS afecto;
        """
    )
