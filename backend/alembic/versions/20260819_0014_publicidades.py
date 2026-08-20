"""Crea tabla publicidades para banners promocionales."""

from alembic import op
import sqlalchemy as sa
from app.core.config import get_settings

revision = "20260819_0014"
down_revision = "20260819_0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    schema = get_settings().database_schema
    op.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {schema}.publicidades (
            id UUID PRIMARY KEY,
            producto_id UUID REFERENCES {schema}.productos(id) ON DELETE SET NULL,
            titulo VARCHAR(200) NOT NULL,
            subtitulo TEXT,
            etiqueta_1 VARCHAR(80),
            etiqueta_2 VARCHAR(80),
            etiqueta_roja VARCHAR(50) NOT NULL DEFAULT 'OFERTA',
            texto_boton VARCHAR(80) NOT NULL DEFAULT 'Aprovechar Beneficio →',
            pie_texto VARCHAR(255),
            imagen_url TEXT,
            color_fondo VARCHAR(60) NOT NULL DEFAULT '#082620',
            orden INTEGER NOT NULL DEFAULT 0,
            activo BOOLEAN NOT NULL DEFAULT TRUE,
            eliminado_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            created_by UUID,
            updated_by UUID
        );

        CREATE INDEX IF NOT EXISTS ix_publicidades_orden ON {schema}.publicidades (orden);
        CREATE INDEX IF NOT EXISTS ix_publicidades_activo ON {schema}.publicidades (activo);
        CREATE INDEX IF NOT EXISTS ix_publicidades_producto_id ON {schema}.publicidades (producto_id);
        CREATE INDEX IF NOT EXISTS ix_publicidades_eliminado_at ON {schema}.publicidades (eliminado_at);
        """
    )


def downgrade() -> None:
    schema = get_settings().database_schema
    op.execute(
        f"""
        DROP TABLE IF EXISTS {schema}.publicidades CASCADE;
        """
    )
