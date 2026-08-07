"""Relaciona pedidos con estados persistidos."""

import uuid

import sqlalchemy as sa
from alembic import op

from app.core.config import get_settings


revision = "20260804_0004"
down_revision = "20260804_0003"
branch_labels = None
depends_on = None

STATE_NAMES = ("Pedido", "Despachado", "Entregado", "Cancelado")


def upgrade() -> None:
    schema = get_settings().database_schema
    estados = sa.table(
        "estados",
        sa.column("id", sa.dialects.postgresql.UUID(as_uuid=True)),
        sa.column("nombre", sa.String()),
        sa.column("activo", sa.Boolean()),
    )
    for name in STATE_NAMES:
        op.execute(
            sa.text(
                f'INSERT INTO "{schema}".estados (id, nombre, activo) '
                "SELECT :id, :name, true "
                f'WHERE NOT EXISTS (SELECT 1 FROM "{schema}".estados WHERE nombre = :name)'
            ).bindparams(id=uuid.uuid4(), name=name)
        )

    op.add_column("pedidos", sa.Column("estado_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True), schema=schema)
    op.execute(
        sa.text(
            f'UPDATE "{schema}".pedidos AS pedido SET estado_id = estado.id '
            f'FROM "{schema}".estados AS estado '
            "WHERE estado.nombre = CASE pedido.estado::text "
            "WHEN 'PEDIDO' THEN 'Pedido' "
            "WHEN 'EN_REPARTO' THEN 'Despachado' "
            "WHEN 'ENTREGADO' THEN 'Entregado' "
            "WHEN 'CANCELADO' THEN 'Cancelado' END"
        )
    )
    op.alter_column("pedidos", "estado_id", nullable=False, schema=schema)
    op.create_foreign_key(
        "fk_pedidos_estado_id",
        "pedidos",
        "estados",
        ["estado_id"],
        ["id"],
        source_schema=schema,
        referent_schema=schema,
    )
    op.create_index("ix_pedidos_estado_id", "pedidos", ["estado_id"], schema=schema)
    op.drop_column("pedidos", "estado", schema=schema)
    op.execute(sa.text(f'DROP TYPE IF EXISTS "{schema}".estado_pedido'))


def downgrade() -> None:
    schema = get_settings().database_schema
    op.execute(sa.text(f'CREATE TYPE "{schema}".estado_pedido AS ENUM (\'PEDIDO\', \'EN_REPARTO\', \'ENTREGADO\', \'CANCELADO\')'))
    op.add_column("pedidos", sa.Column("estado", sa.Enum("PEDIDO", "EN_REPARTO", "ENTREGADO", "CANCELADO", name="estado_pedido", schema=schema), nullable=True), schema=schema)
    op.execute(
        sa.text(
            f'UPDATE "{schema}".pedidos AS pedido SET estado = CASE estado.nombre '
            "WHEN 'Pedido' THEN 'PEDIDO'::estado_pedido "
            "WHEN 'Despachado' THEN 'EN_REPARTO'::estado_pedido "
            "WHEN 'Entregado' THEN 'ENTREGADO'::estado_pedido "
            "ELSE 'CANCELADO'::estado_pedido END "
            f'FROM "{schema}".estados AS estado WHERE pedido.estado_id = estado.id'
        )
    )
    op.alter_column("pedidos", "estado", nullable=False, schema=schema)
    op.drop_index("ix_pedidos_estado_id", table_name="pedidos", schema=schema)
    op.drop_constraint("fk_pedidos_estado_id", "pedidos", schema=schema, type_="foreignkey")
    op.drop_column("pedidos", "estado_id", schema=schema)