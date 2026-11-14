"""Elimina clientes creados erroneamente en la tabla de usuarios y apaga recibe_pedido.

Revision ID: 20261113_0042
Revises: 20261113_0041
Create Date: 2026-11-13
"""

from alembic import op
from app.core.config import get_settings

revision = "20261113_0042"
down_revision = "20261113_0041"
branch_labels = None
depends_on = None


def upgrade() -> None:
    settings = get_settings()
    schema = settings.database_schema

    # 1. Eliminar cualquier usuario que en realidad sea un cliente de la tienda (salvo cuentas del staff)
    op.execute(f"""
        DELETE FROM {schema}.usuarios 
        WHERE LOWER(correo) IN (
            SELECT LOWER(correo) FROM {schema}.clientes WHERE correo IS NOT NULL
        )
        AND LOWER(correo) NOT IN ('roderick.espinoza@gmail.com', 'admin@correodistribuidoratridente.cl', 'pedidos.tridente2026@gmail.com');
    """)

    # 2. Asegurar borrado específico de los correos de clientes reportados
    op.execute(f"""
        DELETE FROM {schema}.usuarios 
        WHERE LOWER(correo) IN ('andres.cortes.meza.98@gmail.com', 'almabyabbie@gmail.com');
    """)

    # 3. Forzar recibe_pedido a false en caso de que quede algún registro rezagado
    op.execute(f"""
        UPDATE {schema}.usuarios 
        SET recibe_pedido = false 
        WHERE LOWER(correo) IN ('andres.cortes.meza.98@gmail.com', 'almabyabbie@gmail.com');
    """)

    # 4. Limpieza de conversaciones en ia_chats que no correspondan a administradores válidos
    op.execute(f"""
        DELETE FROM {schema}.ia_chat_mensajes 
        WHERE chat_id IN (
            SELECT id FROM {schema}.ia_chats 
            WHERE usuario_id NOT IN (SELECT id FROM {schema}.usuarios)
        );
        DELETE FROM {schema}.ia_chats 
        WHERE usuario_id NOT IN (SELECT id FROM {schema}.usuarios);
    """)


def downgrade() -> None:
    pass

