"""Agrega campos celular y recibe_pedido a tabla usuarios."""

from alembic import op
import sqlalchemy as sa


revision = "20260815_0009"
down_revision = "20260812_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE bdtridente.usuarios ADD COLUMN IF NOT EXISTS celular VARCHAR(30)")
    op.execute("ALTER TABLE bdtridente.usuarios ADD COLUMN IF NOT EXISTS recibe_pedido BOOLEAN NOT NULL DEFAULT false")


def downgrade() -> None:
    op.drop_column("usuarios", "recibe_pedido", schema="bdtridente")
    op.drop_column("usuarios", "celular", schema="bdtridente")
