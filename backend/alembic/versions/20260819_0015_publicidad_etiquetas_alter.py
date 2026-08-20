"""Amplia longitud de campos etiqueta_1 y etiqueta_2 en publicidades."""

from alembic import op
import sqlalchemy as sa
from app.core.config import get_settings

revision = "20260819_0015"
down_revision = "20260819_0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    schema = get_settings().database_schema
    op.execute(
        f"""
        ALTER TABLE {schema}.publicidades
        ALTER COLUMN etiqueta_1 TYPE VARCHAR(255),
        ALTER COLUMN etiqueta_2 TYPE VARCHAR(255);
        """
    )


def downgrade() -> None:
    schema = get_settings().database_schema
    op.execute(
        f"""
        ALTER TABLE {schema}.publicidades
        ALTER COLUMN etiqueta_1 TYPE VARCHAR(80),
        ALTER COLUMN etiqueta_2 TYPE VARCHAR(80);
        """
    )
