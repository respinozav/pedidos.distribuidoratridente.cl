"""Crea tablas ia_chats e ia_mensajes para Agente Tridente IA.

Revision ID: 20261014_0036
Revises: 20261001_0035
Create Date: 2026-10-14
"""

from alembic import op
from app.core.config import get_settings

revision = "20261014_0036"
down_revision = "20261001_0035"
branch_labels = None
depends_on = None


def upgrade() -> None:
    schema = get_settings().database_schema
    try:
        op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")
    except Exception:
        pass

    op.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {schema}.ia_chats (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            usuario_id UUID NOT NULL REFERENCES {schema}.usuarios(id) ON DELETE CASCADE,
            titulo VARCHAR(255) NOT NULL DEFAULT 'Nueva conversación',
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        );
        """
    )

    op.execute(
        f"""
        CREATE INDEX IF NOT EXISTS ix_ia_chats_usuario_updated 
            ON {schema}.ia_chats(usuario_id, updated_at DESC);
        """
    )

    op.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {schema}.ia_mensajes (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            chat_id UUID NOT NULL REFERENCES {schema}.ia_chats(id) ON DELETE CASCADE,
            rol VARCHAR(20) NOT NULL,
            contenido TEXT NOT NULL,
            datos_estructurados JSONB NULL,
            herramientas_usadas JSONB NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        );
        """
    )

    op.execute(
        f"""
        CREATE INDEX IF NOT EXISTS ix_ia_mensajes_chat_created 
            ON {schema}.ia_mensajes(chat_id, created_at ASC);
        """
    )


def downgrade() -> None:
    schema = get_settings().database_schema
    op.execute(
        f"""
        DROP TABLE IF EXISTS {schema}.ia_mensajes;
        DROP TABLE IF EXISTS {schema}.ia_chats;
        """
    )
