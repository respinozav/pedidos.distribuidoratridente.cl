from datetime import datetime
from typing import List
from fastapi import APIRouter, HTTPException, Query, Response, status
from sqlalchemy import func, select, desc
from sqlalchemy.orm import Session

from app.api.dependencies import AdminUser, DatabaseSession
from app.models.entities import ConfiguracionAvisos, LogCorreo
from app.schemas.configuracion_avisos import (
    ConfiguracionAvisosResponse,
    ConfiguracionAvisosUpdate,
    LogCorreoResponse,
)

router = APIRouter(tags=["Configuración de Avisos de Cobranza"])


@router.get("/configuracion_avisos", response_model=ConfiguracionAvisosResponse)
def get_configuracion_avisos(database: DatabaseSession, _: AdminUser):
    config = database.scalar(select(ConfiguracionAvisos).filter(ConfiguracionAvisos.id == 1))
    if not config:
        config = ConfiguracionAvisos(
            id=1,
            hora_envio="09:00:00",
            asunto_recordatorio="Recordatorio: Tu crédito vencerá mañana - Distribuidora Tridente",
            plantilla_recordatorio="Hola {{nombre}}, le recordamos que su crédito por {{dias_credito}} días vencerá el {{fecha_vencimiento}}. Favor coordinar el pago.",
            asunto_aviso="Aviso: Tu crédito vence hoy - Distribuidora Tridente",
            plantilla_aviso="Estimado/a {{nombre}}, le informamos que su crédito vence hoy {{fecha_vencimiento}}. Favor regularizar a la brevedad.",
            asunto_vencido="Urgente: Tu crédito se encuentra VENCIDO - Distribuidora Tridente",
            plantilla_vencido="Estimado/a {{nombre}}, le informamos que su crédito por {{dias_credito}} días se encuentra VENCIDO desde el {{fecha_vencimiento}} ({{dias_mora}} días de mora). Favor regularizar su saldo a la brevedad.",
            activo=True,
        )
        database.add(config)
        database.commit()
        database.refresh(config)
    return config


@router.patch("/configuracion_avisos", response_model=ConfiguracionAvisosResponse)
@router.put("/configuracion_avisos", response_model=ConfiguracionAvisosResponse)
def update_configuracion_avisos(
    payload: ConfiguracionAvisosUpdate,
    database: DatabaseSession,
    _: AdminUser,
):
    config = database.scalar(select(ConfiguracionAvisos).filter(ConfiguracionAvisos.id == 1))
    if not config:
        config = ConfiguracionAvisos(
            id=1,
            hora_envio="09:00:00",
            asunto_recordatorio="Recordatorio: Tu crédito vencerá mañana - Distribuidora Tridente",
            plantilla_recordatorio="Hola {{nombre}}, le recordamos que su crédito por {{dias_credito}} días vencerá el {{fecha_vencimiento}}. Favor coordinar el pago.",
            asunto_aviso="Aviso: Tu crédito vence hoy - Distribuidora Tridente",
            plantilla_aviso="Estimado/a {{nombre}}, le informamos que su crédito vence hoy {{fecha_vencimiento}}. Favor regularizar a la brevedad.",
            asunto_vencido="Urgente: Tu crédito se encuentra VENCIDO - Distribuidora Tridente",
            plantilla_vencido="Estimado/a {{nombre}}, le informamos que su crédito por {{dias_credito}} días se encuentra VENCIDO desde el {{fecha_vencimiento}} ({{dias_mora}} días de mora). Favor regularizar su saldo a la brevedad.",
            activo=True,
        )
        database.add(config)

    for field, value in payload.model_dump(exclude_unset=True).items():
        if value is not None:
            # Formatear la hora si viene con o sin segundos
            if field == "hora_envio":
                time_str = str(value).strip()
                if len(time_str) == 5:  # "09:00" -> "09:00:00"
                    time_str += ":00"
                try:
                    parsed_time = datetime.strptime(time_str, "%H:%M:%S").time()
                    setattr(config, field, parsed_time)
                except ValueError:
                    setattr(config, field, time_str)
            else:
                setattr(config, field, value)

    config.actualizado_el = datetime.utcnow()
    database.commit()
    database.refresh(config)
    return config


@router.get("/log_correos", response_model=List[LogCorreoResponse])
def get_log_correos(
    response: Response,
    database: DatabaseSession,
    _: AdminUser,
    limit: int = Query(default=30, ge=1, le=100),
):
    total = database.scalar(select(func.count(LogCorreo.id))) or 0
    response.headers["X-Total-Count"] = str(total)
    response.headers["Access-Control-Expose-Headers"] = "X-Total-Count"
    statement = (
        select(LogCorreo)
        .order_by(desc(LogCorreo.enviado_el))
        .limit(limit)
    )
    logs = list(database.scalars(statement))
    return logs


@router.post("/configuracion_avisos/ejecutar")
def trigger_procesar_avisos(
    database: DatabaseSession,
    _: AdminUser,
    forzar_reenvio: bool = Query(default=False, description="Reenviar aunque ya se haya despachado hoy"),
):
    from app.services.cobranzas import procesar_avisos_cobranza_smtp

    resultado = procesar_avisos_cobranza_smtp(database, forzar_reenvio=forzar_reenvio)
    return resultado

