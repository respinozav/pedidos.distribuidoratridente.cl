"""Crea el rol COLABORADOR si no existe."""

from uuid import uuid4
from alembic import op
from sqlalchemy import text
from app.core.config import get_settings

revision = "20260909_0029"
down_revision = "20260908_0028"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    schema = get_settings().database_schema
    new_id = str(uuid4())
    bind.execute(
        text(
            f"""
            INSERT INTO {schema}.roles (id, nombre, activo, created_at, updated_at)
            SELECT '{new_id}'::uuid, 'COLABORADOR', true, NOW(), NOW()
            WHERE NOT EXISTS (
                SELECT 1 FROM {schema}.roles WHERE UPPER(nombre) = 'COLABORADOR'
            );
            """
        )
    )


def downgrade() -> None:
    pass
