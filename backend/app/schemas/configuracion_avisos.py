from datetime import datetime, time
from uuid import UUID
from typing import Optional, Union
from pydantic import BaseModel, ConfigDict, Field, field_validator


class ConfiguracionAvisosBase(BaseModel):
    hora_envio: Optional[Union[time, str]] = "09:00:00"
    asunto_recordatorio: Optional[str] = "Recordatorio: Tu crédito vencerá mañana - Distribuidora Tridente"
    plantilla_recordatorio: Optional[str] = (
        "Hola {{nombre}}, le recordamos que su crédito por {{dias_credito}} días vencerá el {{fecha_vencimiento}}. Favor coordinar el pago."
    )
    asunto_aviso: Optional[str] = "Aviso: Tu crédito vence hoy - Distribuidora Tridente"
    plantilla_aviso: Optional[str] = (
        "Estimado/a {{nombre}}, le informamos que su crédito vence hoy {{fecha_vencimiento}}. Favor regularizar a la brevedad."
    )
    asunto_vencido: Optional[str] = "Urgente: Tu crédito se encuentra VENCIDO - Distribuidora Tridente"
    plantilla_vencido: Optional[str] = (
        "Estimado/a {{nombre}}, le informamos que su crédito por {{dias_credito}} días se encuentra VENCIDO desde el {{fecha_vencimiento}} ({{dias_mora}} días de mora). Favor regularizar su saldo a la brevedad."
    )
    activo: Optional[bool] = True


class ConfiguracionAvisosUpdate(BaseModel):
    hora_envio: Optional[Union[time, str]] = None
    asunto_recordatorio: Optional[str] = None
    plantilla_recordatorio: Optional[str] = None
    asunto_aviso: Optional[str] = None
    plantilla_aviso: Optional[str] = None
    asunto_vencido: Optional[str] = None
    plantilla_vencido: Optional[str] = None
    activo: Optional[bool] = None


class ConfiguracionAvisosResponse(BaseModel):
    id: int
    hora_envio: Union[time, str]
    asunto_recordatorio: str
    plantilla_recordatorio: str
    asunto_aviso: str
    plantilla_aviso: str
    asunto_vencido: Optional[str] = "Urgente: Tu crédito se encuentra VENCIDO - Distribuidora Tridente"
    plantilla_vencido: Optional[str] = "Estimado/a {{nombre}}, le informamos que su crédito por {{dias_credito}} días se encuentra VENCIDO desde el {{fecha_vencimiento}} ({{dias_mora}} días de mora). Favor regularizar su saldo a la brevedad."
    activo: bool
    actualizado_el: datetime

    @field_validator("hora_envio", mode="before")
    @classmethod
    def serialize_hora(cls, v: Union[time, str]) -> str:
        if isinstance(v, time):
            return v.strftime("%H:%M:%S")
        return str(v)

    model_config = ConfigDict(from_attributes=True)


class LogCorreoResponse(BaseModel):
    id: UUID
    credito_id: UUID
    cliente_id: Optional[UUID] = None
    destinatario: str
    tipo: str
    asunto: Optional[str] = None
    cuerpo_enviado: str
    estado: str
    net_request_id: Optional[int] = None
    enviado_el: datetime

    model_config = ConfigDict(from_attributes=True)
