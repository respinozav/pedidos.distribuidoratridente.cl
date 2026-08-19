"""Agrega campo orden a tabla categorias."""

from alembic import op
import sqlalchemy as sa
from app.core.config import get_settings

revision = "20260819_0013"
down_revision = "20260818_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    schema = get_settings().database_schema
    op.execute(
        f"""
        ALTER TABLE {schema}.categorias
        ADD COLUMN IF NOT EXISTS orden INTEGER NOT NULL DEFAULT 0;
        """
    )


def downgrade() -> None:
    schema = get_settings().database_schema
    op.execute(
        f"""
        ALTER TABLE {schema}.categorias
        DROP COLUMN IF EXISTS orden;
        """
    )
