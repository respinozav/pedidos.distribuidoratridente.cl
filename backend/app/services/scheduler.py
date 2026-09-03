"""
Background worker para ejecutar la evaluación de cobranzas en FastAPI de forma continua.
Verifica cada 60 segundos si la hora actual de Chile (America/Santiago) coincide con la 'hora_envio'
configurada en configuracion_avisos, y si aún no se ha ejecutado hoy, despacha los correos.
"""

import asyncio
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.entities import ConfiguracionAvisos
from app.services.cobranzas import procesar_avisos_cobranza_smtp

logger = logging.getLogger(__name__)
CHILE_TZ = ZoneInfo("America/Santiago")

_ultimo_dia_ejecutado: str | None = None


async def cobranzas_scheduler_loop() -> None:
    global _ultimo_dia_ejecutado
    logger.info("Iniciando background scheduler de cobranzas...")

    while True:
        try:
            ahora = datetime.now(CHILE_TZ)
            hoy_str = ahora.strftime("%Y-%m-%d")

            # Solo verificamos si no se ha ejecutado hoy en esta fecha
            if _ultimo_dia_ejecutado != hoy_str:
                with SessionLocal() as db:
                    config = db.scalar(select(ConfiguracionAvisos).filter(ConfiguracionAvisos.id == 1))
                    if config and config.activo:
                        hora_cfg = config.hora_envio  # datetime.time
                        # Comparar si la hora y minuto coinciden o ya pasaron hoy
                        if (ahora.hour, ahora.minute) >= (hora_cfg.hour, hora_cfg.minute):
                            logger.info(
                                "Disparando job diario de cobranzas para la fecha %s (hora actual: %s, hora programada: %s)",
                                hoy_str,
                                ahora.strftime("%H:%M:%S"),
                                hora_cfg.strftime("%H:%M:%S"),
                            )
                            resultado = procesar_avisos_cobranza_smtp(db)
                            logger.info("Resultado job de cobranzas: %s", resultado)
                            _ultimo_dia_ejecutado = hoy_str

        except asyncio.CancelledError:
            logger.info("Scheduler de cobranzas cancelado.")
            break
        except Exception as e:
            logger.error("Error en el ciclo del scheduler de cobranzas: %s", e)

        # Esperar 60 segundos antes de la siguiente verificación
        try:
            await asyncio.sleep(60)
        except asyncio.CancelledError:
            break
