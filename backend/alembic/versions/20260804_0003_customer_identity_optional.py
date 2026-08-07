"""Permite clientes identificados por RUT, nombre o celular."""

from alembic import op


revision = "20260804_0003"
down_revision = "20260804_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("clientes", "rut", existing_type=op.f("VARCHAR"), nullable=True)
    op.alter_column("clientes", "nombre", existing_type=op.f("VARCHAR"), nullable=True)
    op.alter_column("clientes", "celular", existing_type=op.f("VARCHAR"), nullable=True)


def downgrade() -> None:
    op.alter_column("clientes", "celular", existing_type=op.f("VARCHAR"), nullable=False)
    op.alter_column("clientes", "nombre", existing_type=op.f("VARCHAR"), nullable=False)
    op.alter_column("clientes", "rut", existing_type=op.f("VARCHAR"), nullable=False)