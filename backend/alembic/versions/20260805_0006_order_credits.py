"""Registra créditos originados en entregas sin pago."""

import sqlalchemy as sa
from alembic import op

from app.core.config import get_settings


revision = "20260805_0006"
down_revision = "20260805_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    schema = get_settings().database_schema
    op.create_table(
        "creditos",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("cliente_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pedido_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column("dias_credito", sa.Integer(), nullable=False),
        sa.Column("fecha_entrega", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fecha_vencimiento", sa.DateTime(timezone=True), nullable=False),
        sa.Column("pagado", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("fecha_pago", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("created_by", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["cliente_id"], [f"{schema}.clientes.id"]),
        sa.ForeignKeyConstraint(["pedido_id"], [f"{schema}.pedidos.id"]),
        schema=schema,
    )
    op.create_index("ix_creditos_cliente_id", "creditos", ["cliente_id"], schema=schema)
    op.create_index("ix_creditos_pedido_id", "creditos", ["pedido_id"], unique=True, schema=schema)


def downgrade() -> None:
    schema = get_settings().database_schema
    op.drop_table("creditos", schema=schema)