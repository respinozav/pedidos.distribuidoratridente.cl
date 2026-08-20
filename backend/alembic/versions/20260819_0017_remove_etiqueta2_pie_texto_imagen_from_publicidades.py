"""Elimina columnas etiqueta_2, pie_texto e imagen_url de la tabla publicidades."""

from alembic import op
import sqlalchemy as sa
from app.core.config import get_settings

revision = "20260819_0017"
down_revision = "20260819_0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    schema = get_settings().database_schema
    op.execute(
        f"""
        ALTER TABLE {schema}.publicidades
        DROP COLUMN IF EXISTS etiqueta_2,
        DROP COLUMN IF EXISTS pie_texto,
        DROP COLUMN IF EXISTS imagen_url;
        """
    )


def downgrade() -> None:
    schema = get_settings().database_schema
    op.execute(
        f"""
        ALTER TABLE {schema}.publicidades
        ADD COLUMN IF NOT EXISTS etiqueta_2 VARCHAR(255),
        ADD COLUMN IF NOT EXISTS pie_texto VARCHAR(255),
        ADD COLUMN IF NOT EXISTS imagen_url TEXT;
        """
    )
