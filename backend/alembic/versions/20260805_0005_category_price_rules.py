"""Configura el porcentaje aplicable por categoría."""

import sqlalchemy as sa
from alembic import op

from app.core.config import get_settings


revision = "20260805_0005"
down_revision = "20260804_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    schema = get_settings().database_schema
    op.add_column(
        "categorias",
        sa.Column("usa_porcentaje_cliente", sa.Boolean(), nullable=False, server_default=sa.true()),
        schema=schema,
    )
    op.add_column(
        "categorias",
        sa.Column("porcentaje", sa.Numeric(5, 2), nullable=False, server_default="0"),
        schema=schema,
    )
    op.alter_column("categorias", "usa_porcentaje_cliente", server_default=None, schema=schema)
    op.alter_column("categorias", "porcentaje", server_default=None, schema=schema)


def downgrade() -> None:
    schema = get_settings().database_schema
    op.drop_column("categorias", "porcentaje", schema=schema)
    op.drop_column("categorias", "usa_porcentaje_cliente", schema=schema)