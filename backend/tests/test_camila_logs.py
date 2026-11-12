from decimal import Decimal
from uuid import uuid4
from sqlalchemy import text
from app.core.database import SessionLocal, engine
from app.core.config import get_settings
from app.models.entities import CamilaLog, Usuario, Rol
from app.schemas.dto import CamilaLogCreate
from app.controllers.routes import (
    create_camila_log,
    list_camila_logs,
    camila_logs_stats,
)


def ensure_table_exists():
    schema = get_settings().database_schema
    with engine.begin() as conn:
        conn.execute(text(f"ALTER TABLE {schema}.usuarios ADD COLUMN IF NOT EXISTS recibe_camila_whatsapp BOOLEAN NOT NULL DEFAULT false;"))
        conn.execute(text(f"ALTER TABLE {schema}.usuarios ADD COLUMN IF NOT EXISTS recibe_camila_email BOOLEAN NOT NULL DEFAULT false;"))
        conn.execute(
            text(
                f"""
            CREATE TABLE IF NOT EXISTS {schema}.camila_logs (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                razon_social VARCHAR(255) NOT NULL,
                whatsapp VARCHAR(50),
                correo VARCHAR(255),
                conversacion TEXT,
                resumen TEXT,
                total_estimado NUMERIC(12, 2),
                enviado_whatsapp BOOLEAN NOT NULL DEFAULT false,
                enviado_email BOOLEAN NOT NULL DEFAULT false,
                destinatarios_whatsapp TEXT,
                destinatarios_email TEXT,
                estado VARCHAR(50) NOT NULL DEFAULT 'COMPLETADA',
                origen VARCHAR(100) NOT NULL DEFAULT 'WEB_CAMILA',
                metadata_extra JSONB,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            );
            """
            )
        )


def test_camila_logs_crud_and_stats():
    ensure_table_exists()
    db = SessionLocal()
    try:
        # Get or mock an admin user
        admin = db.query(Usuario).first()
        if not admin:
            rol = db.query(Rol).first()
            admin = Usuario(
                nombre="Admin Test",
                correo="admintest@tridente.cl",
                password_hash="fakehash",
                rol_id=rol.id if rol else uuid4(),
                activo=True,
            )

        test_razon = f"Empresa Test Camila {uuid4().hex[:6]}"
        test_wsp = "+56912345678"
        test_mail = f"contacto_{uuid4().hex[:6]}@cliente.cl"

        # 1. Create a log via controller
        created = create_camila_log(
            payload=CamilaLogCreate(
                razon_social=test_razon,
                whatsapp=test_wsp,
                correo=test_mail,
                conversacion="Cliente: Hola necesito 10 cajas de resmas\nCamila: Perfecto, total estimado $45.000",
                resumen="Venta de 10 cajas de resmas tamaño carta",
                total_estimado=Decimal("45000.00"),
                enviado_whatsapp=True,
                enviado_email=True,
                destinatarios_whatsapp="+56944488407",
                destinatarios_email="pedidos.tridente2026@gmail.com",
                estado="COMPLETADA",
                origen="WEB_CAMILA",
            ),
            database=db,
        )

        assert created.id is not None
        assert created.razon_social == test_razon
        assert created.whatsapp == test_wsp
        assert created.correo == test_mail
        assert created.enviado_whatsapp is True
        assert created.enviado_email is True
        assert created.total_estimado == Decimal("45000.00")

        # 2. Query list with search
        page_result = list_camila_logs(
            database=db,
            _=admin,
            search=test_razon,
            page=1,
            page_size=10,
        )
        assert page_result.total >= 1
        found = any(item.id == created.id for item in page_result.items)
        assert found, "El log creado debe aparecer en la búsqueda"

        # 3. Query stats
        stats = camila_logs_stats(database=db, _=admin)
        assert stats.total >= 1
        assert stats.con_whatsapp >= 1
        assert stats.con_correo >= 1
        assert stats.ambos_canales >= 1

        print("TEST CAMILA LOGS OK!")
    finally:
        db.close()


if __name__ == "__main__":
    test_camila_logs_crud_and_stats()
