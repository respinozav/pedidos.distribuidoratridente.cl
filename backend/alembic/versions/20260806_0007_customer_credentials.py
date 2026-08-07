"""Agrega credenciales de acceso para clientes."""

import sqlalchemy as sa
from alembic import op

from app.core.config import get_settings


revision = "20260806_0007"
down_revision = "20260805_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    schema = get_settings().database_schema
    op.add_column("clientes", sa.Column("password_hash", sa.String(length=255), nullable=True), schema=schema)
    op.create_index("ix_clientes_correo", "clientes", ["correo"], unique=True, schema=schema)


def downgrade() -> None:
    schema = get_settings().database_schema
    op.drop_index("ix_clientes_correo", table_name="clientes", schema=schema)
    op.drop_column("clientes", "password_hash", schema=schema)