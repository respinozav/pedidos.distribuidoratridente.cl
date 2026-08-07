"""Amplia la columna de imagen de productos para contenido Base64."""

import sqlalchemy as sa
from alembic import op

from app.core.config import get_settings

revision = "20260804_0002"
down_revision = "20260804_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "productos",
        "imagen_url",
        existing_type=sa.String(length=500),
        type_=sa.Text(),
        existing_nullable=True,
        schema=get_settings().database_schema,
    )


def downgrade() -> None:
    op.alter_column(
        "productos",
        "imagen_url",
        existing_type=sa.Text(),
        type_=sa.String(length=500),
        existing_nullable=True,
        schema=get_settings().database_schema,
    )