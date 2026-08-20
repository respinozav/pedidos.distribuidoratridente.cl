"""Elimina columnas activo y eliminado_at de publicidades para eliminacion directa y sin historico de estado."""

from alembic import op
import sqlalchemy as sa
from app.core.config import get_settings

revision = "20260819_0016"
down_revision = "20260819_0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    schema = get_settings().database_schema
    op.execute(
        f"""
        DROP INDEX IF EXISTS {schema}.ix_publicidades_activo;
        DROP INDEX IF EXISTS {schema}.ix_publicidades_eliminado_at;

        ALTER TABLE {schema}.publicidades
        DROP COLUMN IF EXISTS activo,
        DROP COLUMN IF EXISTS eliminado_at;
        """
    )


def downgrade() -> None:
    schema = get_settings().database_schema
    op.execute(
        f"""
        ALTER TABLE {schema}.publicidades
        ADD COLUMN IF NOT EXISTS activo BOOLEAN NOT NULL DEFAULT TRUE,
        ADD COLUMN IF NOT EXISTS eliminado_at TIMESTAMPTZ;

        CREATE INDEX IF NOT EXISTS ix_publicidades_activo ON {schema}.publicidades (activo);
        CREATE INDEX IF NOT EXISTS ix_publicidades_eliminado_at ON {schema}.publicidades (eliminado_at);
        """
    )
