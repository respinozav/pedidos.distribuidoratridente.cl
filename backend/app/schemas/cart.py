from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CartItemInput(BaseModel):
    producto_id: UUID
    cantidad: int = Field(gt=0, description="Cantidad mayor a 0")
    tipo_empaque: str = Field(default="unidad")
    cantidad_caja: Optional[int] = None


class CartItemUpdate(BaseModel):
    cantidad: int = Field(gt=0, description="Cantidad mayor a 0")


class CartItemOutput(BaseModel):
    id: UUID
    producto_id: UUID
    codigo_producto: str
    nombre_producto: str
    imagen_url: Optional[str] = None
    cantidad: int
    tipo_empaque: str
    cantidad_caja: Optional[int] = None
    precio_unitario: Decimal
    subtotal: Decimal
    stock_actual: int

    model_config = ConfigDict(from_attributes=True)


class CartOutput(BaseModel):
    id: UUID
    cliente_id: UUID
    direccion_id: Optional[UUID] = None
    items: list[CartItemOutput] = []
    total_items: int = 0
    total_unidades: int = 0
    total: Decimal = Decimal("0.00")
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AdminCartItemOutput(BaseModel):
    id: UUID
    producto_id: UUID
    codigo_producto: str
    nombre_producto: str
    cantidad: int
    tipo_empaque: str
    cantidad_caja: Optional[int] = None
    unidades_totales: int
    precio_unitario: Decimal
    subtotal: Decimal


class AdminActiveCartOutput(BaseModel):
    id: UUID
    cliente_id: UUID
    cliente_rut: Optional[str] = None
    cliente_nombre: str
    cliente_correo: Optional[str] = None
    cliente_celular: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    total_items: int
    total_unidades: int
    total: Decimal
    expira_en_segundos: int
    expirado: bool
    items: list[AdminCartItemOutput]
