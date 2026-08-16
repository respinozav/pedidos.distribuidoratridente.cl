"""Agrega campos celular y recibe_pedido a tabla usuarios."""

from alembic import op
import sqlalchemy as sa


revision = "20260815_0009"
down_revision = "20260812_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "usuarios",
        sa.Column("celular", sa.String(length=30), nullable=True),
        schema="bdtridente",
    )
    op.add_column(
        "usuarios",
        sa.Column("recibe_pedido", sa.Boolean(), nullable=False, server_default="false"),
        schema="bdtridente",
    )


def downgrade() -> None:
    op.drop_column("usuarios", "recibe_pedido", schema="bdtridente")
    op.drop_column("usuarios", "celular", schema="bdtridente")
