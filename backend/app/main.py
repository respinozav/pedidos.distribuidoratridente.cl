import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.controllers.routes import router
from app.core.config import get_settings
from app.services.scheduler import cobranzas_scheduler_loop

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Asegurar que las columnas nuevas existan en la base de datos sin depender de migraciones manuales
    try:
        from app.core.database import engine
        from sqlalchemy import text
        schema = settings.database_schema
        with engine.begin() as conn:
            conn.execute(text(f"ALTER TABLE {schema}.usuarios ADD COLUMN IF NOT EXISTS recibe_camila_whatsapp BOOLEAN NOT NULL DEFAULT false;"))
            conn.execute(text(f"ALTER TABLE {schema}.usuarios ADD COLUMN IF NOT EXISTS recibe_camila_email BOOLEAN NOT NULL DEFAULT false;"))
            conn.execute(text(f"""
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
            """))
            conn.execute(text(f"CREATE INDEX IF NOT EXISTS ix_camila_logs_created_at ON {schema}.camila_logs (created_at DESC);"))
            conn.execute(text(f"CREATE INDEX IF NOT EXISTS ix_camila_logs_razon_social ON {schema}.camila_logs (razon_social);"))
            conn.execute(text(f"CREATE INDEX IF NOT EXISTS ix_camila_logs_whatsapp ON {schema}.camila_logs (whatsapp);"))
            conn.execute(text(f"CREATE INDEX IF NOT EXISTS ix_camila_logs_correo ON {schema}.camila_logs (correo);"))
            conn.execute(text(f"CREATE INDEX IF NOT EXISTS ix_camila_logs_estado ON {schema}.camila_logs (estado);"))
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning("No se pudo auto-aplicar columnas en usuarios: %s", exc)

    # Iniciar background task de cobranzas
    scheduler_task = asyncio.create_task(cobranzas_scheduler_loop())
    yield
    scheduler_task.cancel()
    try:
        await scheduler_task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title="Sistema de Pedidos Distribuidora Tridente API",
    version="0.1.0",
    openapi_url="/api/openapi.json",
    docs_url="/api/docs",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[*settings.cors_origin_list, "http://localhost:5173", "http://localhost:5174", "http://localhost:5175", "http://localhost:5176", "http://127.0.0.1:5173", "http://127.0.0.1:5174", "http://127.0.0.1:5175", "http://127.0.0.1:5176"],
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)


@app.get("/api/health", tags=["Sistema"])
async def health_check() -> dict[str, str]:
    return {"status": "ok"}