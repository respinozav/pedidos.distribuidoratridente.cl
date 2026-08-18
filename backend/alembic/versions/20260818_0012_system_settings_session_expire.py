"""Agrega jwt_access_token_expire_minutes a system_settings."""

from alembic import op
import sqlalchemy as sa
from app.core.config import get_settings

revision = "20260818_0012"
down_revision = "20260817_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    schema = get_settings().database_schema
    op.execute(
        f"""
        ALTER TABLE {schema}.system_settings
        ADD COLUMN IF NOT EXISTS jwt_access_token_expire_minutes INTEGER DEFAULT 60;
        """
    )


def downgrade() -> None:
    schema = get_settings().database_schema
    op.execute(
        f"""
        ALTER TABLE {schema}.system_settings
        DROP COLUMN IF EXISTS jwt_access_token_expire_minutes;
        """
    )
