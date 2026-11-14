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
            
            # Limpieza y seguridad crítica: Eliminar de la tabla usuarios cualquier cliente que se haya creado erróneamente
            # y apagar cualquier flag recibe_pedido en correos de clientes
            conn.execute(text(f"""
                DELETE FROM {schema}.usuarios 
                WHERE LOWER(correo) IN (
                    SELECT LOWER(correo) FROM {schema}.clientes WHERE correo IS NOT NULL
                )
                AND LOWER(correo) NOT IN ('roderick.espinoza@gmail.com', 'admin@correodistribuidoratridente.cl', 'pedidos.tridente2026@gmail.com');
            """))
            conn.execute(text(f"""
                DELETE FROM {schema}.usuarios 
                WHERE LOWER(correo) IN ('andres.cortes.meza.98@gmail.com', 'almabyabbie@gmail.com');
            """))
            conn.execute(text(f"""
                UPDATE {schema}.usuarios 
                SET recibe_pedido = false 
                WHERE LOWER(correo) IN ('andres.cortes.meza.98@gmail.com', 'almabyabbie@gmail.com');
            """))
            conn.execute(text(f"""
                DELETE FROM {schema}.ia_chat_mensajes 
                WHERE chat_id IN (
                    SELECT id FROM {schema}.ia_chats 
                    WHERE usuario_id NOT IN (SELECT id FROM {schema}.usuarios)
                );
                DELETE FROM {schema}.ia_chats 
                WHERE usuario_id NOT IN (SELECT id FROM {schema}.usuarios);
            """))
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

            # Actualizar imágenes en alta definición para la categoría DESECHABLES
            from pathlib import Path
            import base64

            static_desechables = Path(__file__).resolve().parent / "static" / "images" / "desechables"
            if static_desechables.exists():
                product_map = {
                    "760": "bolsa_camiseta_blanca.jpg",
                    "761": "bolsa_camiseta_blanca.jpg",
                    "762": "bolsa_camiseta_blanca.jpg",
                    "763": "bolsa_camiseta_blanca.jpg",
                    "764": "bolsa_taco_transparente.jpg",
                    "765": "vaso_transparente_300cc.jpg",
                    "766": "vaso_transparente_500cc.jpg",
                    "767": "vaso_polipapel_blanco.jpg",
                    "768": "vaso_polipapel_diseno.jpg",
                    "769": "vaso_polipapel_kraft.jpg",
                    "770": "pinchos_bambu.jpg",
                    "771": "pinchos_bambu.jpg",
                    "772": "pinchos_bambu.jpg",
                    "773": "revolvedor_madera.jpg",
                    "774": "portacomidas_sin_division.jpg",
                    "775": "portacomidas_con_division.jpg",
                    "776": "contenedor_marmita.jpg",
                    "777": "contenedor_marmita.jpg",
                    "778": "contenedor_sandwich.jpg",
                }
                cache_imgs = {}
                for fn in set(product_map.values()):
                    img_file = static_desechables / fn
                    if img_file.exists():
                        cache_imgs[fn] = base64.b64encode(img_file.read_bytes()).decode("utf-8")

                for cod, fn in product_map.items():
                    b64_val = cache_imgs.get(fn)
                    if b64_val:
                        conn.execute(
                            text(f"UPDATE {schema}.productos SET imagen_url = :b64 WHERE codigo = :codigo"),
                            {"b64": b64_val, "codigo": cod}
                        )
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