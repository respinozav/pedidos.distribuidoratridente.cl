"""Crea la tabla pedido_notificacion_logs para registrar auditoria de envios de correo y WhatsApp."""

from alembic import op
import sqlalchemy as sa
from app.core.config import get_settings

revision = "20260817_0011"
down_revision = "20260816_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    schema = get_settings().database_schema
    op.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {schema}.pedido_notificacion_logs (
            id UUID PRIMARY KEY,
            pedido_id UUID REFERENCES {schema}.pedidos(id) ON DELETE CASCADE,
            canal VARCHAR(30) NOT NULL,
            tipo VARCHAR(50) NOT NULL,
            destinatario VARCHAR(255) NOT NULL,
            estado VARCHAR(30) NOT NULL,
            mensaje TEXT,
            error TEXT,
            duracion_ms INTEGER,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            created_by UUID,
            updated_by UUID
        );

        CREATE INDEX IF NOT EXISTS ix_pedido_notificacion_logs_pedido_id 
            ON {schema}.pedido_notificacion_logs (pedido_id);

        CREATE INDEX IF NOT EXISTS ix_pedido_notificacion_logs_canal_estado 
            ON {schema}.pedido_notificacion_logs (canal, estado);

        CREATE INDEX IF NOT EXISTS ix_pedido_notificacion_logs_created_at 
            ON {schema}.pedido_notificacion_logs (created_at DESC);
        """
    )


def downgrade() -> None:
    schema = get_settings().database_schema
    op.execute(f"DROP TABLE IF EXISTS {schema}.pedido_notificacion_logs CASCADE;")
