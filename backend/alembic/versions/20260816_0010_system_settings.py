"""Crea la tabla system_settings para configuracion global de SMTP y WhatsApp."""

from alembic import op
import sqlalchemy as sa
from app.core.config import get_settings

revision = "20260816_0010"
down_revision = "20260815_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    schema = get_settings().database_schema
    op.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {schema}.system_settings (
            id SERIAL PRIMARY KEY,
            smtp_host VARCHAR,
            smtp_port INTEGER,
            smtp_username VARCHAR,
            smtp_password VARCHAR,
            smtp_from_email VARCHAR,
            smtp_from_name VARCHAR,
            whatsapp_enabled BOOLEAN NOT NULL DEFAULT false,
            whatsapp_api_key VARCHAR,
            whatsapp_phone_number VARCHAR
        );
        """
    )


def downgrade() -> None:
    schema = get_settings().database_schema
    op.execute(f"DROP TABLE IF EXISTS {schema}.system_settings")
