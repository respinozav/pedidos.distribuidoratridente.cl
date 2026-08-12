"""Agrega campo en_catalogo_publico a tabla categorias."""

from alembic import op
import sqlalchemy as sa


revision = "20260812_0008"
down_revision = "20260806_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "categorias",
        sa.Column("en_catalogo_publico", sa.Boolean(), nullable=False, server_default="true"),
        schema="bdtridente",
    )


def downgrade() -> None:
    op.drop_column("categorias", "en_catalogo_publico", schema="bdtridente")
