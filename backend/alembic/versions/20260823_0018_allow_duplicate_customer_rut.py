"""Permite RUTs repetidos en clientes para múltiples locales o correos.

Revision ID: 20260823_0018
Revises: 20260819_0017
Create Date: 2026-08-23
"""

from alembic import op
from app.core.config import get_settings

revision = "20260823_0018"
down_revision = "20260819_0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    schema = get_settings().database_schema
    op.execute(
        f"""
        DO $$
        DECLARE
            r RECORD;
        BEGIN
            FOR r IN (
                SELECT constraint_name
                FROM information_schema.table_constraints
                WHERE table_schema = '{schema}'
                  AND table_name = 'clientes'
                  AND constraint_type = 'UNIQUE'
                  AND constraint_name IN (
                      SELECT tc.constraint_name
                      FROM information_schema.table_constraints tc
                      JOIN information_schema.constraint_column_usage ccu
                        ON tc.constraint_name = ccu.constraint_name
                       AND tc.table_schema = ccu.table_schema
                      WHERE tc.table_schema = '{schema}'
                        AND tc.table_name = 'clientes'
                        AND ccu.column_name = 'rut'
                  )
            ) LOOP
                EXECUTE 'ALTER TABLE {schema}.clientes DROP CONSTRAINT IF EXISTS ' || quote_ident(r.constraint_name);
            END LOOP;
        END $$;
        """
    )
    op.execute(
        f"""
        DROP INDEX IF EXISTS {schema}.ix_clientes_rut;
        DROP INDEX IF EXISTS {schema}.clientes_rut_key;
        CREATE INDEX IF NOT EXISTS ix_clientes_rut ON {schema}.clientes (rut);
        """
    )


def downgrade() -> None:
    schema = get_settings().database_schema
    op.execute(
        f"""
        DROP INDEX IF EXISTS {schema}.ix_clientes_rut;
        CREATE UNIQUE INDEX IF NOT EXISTS ix_clientes_rut ON {schema}.clientes (rut);
        """
    )
