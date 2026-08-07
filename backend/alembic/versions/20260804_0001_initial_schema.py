"""Crea el esquema bdtridente y las tablas iniciales."""

from alembic import op
from sqlalchemy import text

from app.core.config import get_settings
from app.core.database import Base
import app.models  # noqa: F401 - registra los modelos en Base.metadata

revision = "20260804_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    schema = get_settings().database_schema
    bind.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))
    Base.metadata.create_all(bind=bind, checkfirst=True)


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind(), checkfirst=True)