import base64
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator



class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Page(BaseModel):
    items: list[ORMModel]
    total: int


class CategoryInput(BaseModel):
    nombre: str = Field(min_length=2, max_length=120)
    orden: int | None = Field(default=None)
    usa_porcentaje_cliente: bool = True
    porcentaje: Decimal = Field(default=0, ge=0, le=100, max_digits=5, decimal_places=2)
    activo: bool = True
    en_catalogo_publico: bool = True


class CategoryOutput(CategoryInput, ORMModel):
    id: UUID


class ProductInput(BaseModel):
    categoria_id: UUID
    codigo: str = Field(min_length=1, max_length=50)
    nombre: str = Field(min_length=2, max_length=180)
    precio: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    cantidad: int
    imagen_url: str | None = Field(default=None, max_length=7_000_000)
    activo: bool = True

    @field_validator("nombre")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("codigo")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("imagen_url")
    @classmethod
    def validate_jpeg_base64(cls, value: str | None) -> str | None:
        if value is None:
            return None
        try:
            image = base64.b64decode(value, validate=True)
        except ValueError as error:
            raise ValueError("La imagen debe estar codificada en Base64") from error
        if not image.startswith(b"\xff\xd8\xff"):
            raise ValueError("La imagen debe ser un archivo JPG")
        if len(image) > 5 * 1024 * 1024:
            raise ValueError("La imagen JPG no puede superar 5 MB")
        return value


class ProductOutput(ProductInput, ORMModel):
    id: UUID
    precio_cliente: Decimal | None = None
    categoria: CategoryOutput | None = None


class ProductPage(BaseModel):
    items: list[ProductOutput]
    total: int
    page: int
    page_size: int


class AddressInput(BaseModel):
    direccion: str = Field(min_length=3)
    comuna: str | None = Field(default=None, max_length=100)
    principal: bool = False
    activo: bool = True


class AddressOutput(AddressInput, ORMModel):
    id: UUID
    cliente_id: UUID


class CustomerInput(BaseModel):
    rut: str | None = Field(default=None, max_length=20)
    nombre: str | None = Field(default=None, max_length=180)
    celular: str | None = Field(default=None, max_length=30)
    correo: EmailStr | None = None
    porcentaje: Decimal = Field(default=0, ge=0, le=100, max_digits=5, decimal_places=2)
    activo: bool = True

    @field_validator("rut", "nombre", "celular", mode="before")
    @classmethod
    def empty_values_to_none(cls, value: str | None) -> str | None:
        return value.strip() or None if isinstance(value, str) else value

    def model_post_init(self, __context: object) -> None:
        if not any((self.rut, self.nombre, self.celular)):
            raise ValueError("Debes indicar RUT, nombre o celular")


class CustomerOutput(CustomerInput, ORMModel):
    id: UUID
    direcciones: list[AddressOutput] = []


class CustomerPage(BaseModel):
    items: list[CustomerOutput]
    total: int
    page: int
    page_size: int


class CustomerCreate(CustomerInput):
    correo: EmailStr
    password: str = Field(min_length=8, max_length=128)


class CustomerUpdate(CustomerInput):
    password: str | None = Field(default=None, min_length=8, max_length=128)


class CustomerLogin(BaseModel):
    correo: EmailStr
    password: str = Field(min_length=8, max_length=128)


class CustomerProfileUpdate(BaseModel):
    nombre: str | None = Field(default=None, max_length=180)
    celular: str | None = Field(default=None, max_length=30)

    @field_validator("nombre", "celular", mode="before")
    @classmethod
    def empty_values_to_none(cls, value: str | None) -> str | None:
        return value.strip() or None if isinstance(value, str) else value


class CustomerPasswordUpdate(BaseModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class UserLogin(BaseModel):
    correo: EmailStr
    password: str = Field(min_length=8)


class RoleOutput(ORMModel):
    id: UUID
    nombre: str
    activo: bool


class UserInput(BaseModel):
    nombre: str = Field(min_length=2, max_length=150)
    correo: EmailStr
    celular: str | None = Field(default=None, max_length=30)
    recibe_pedido: bool = False
    rol_id: UUID
    activo: bool = True

    @field_validator("celular", mode="before")
    @classmethod
    def empty_celular_to_none(cls, value: str | None) -> str | None:
        return value.strip() or None if isinstance(value, str) else value


class UserCreate(UserInput):
    password: str = Field(min_length=8, max_length=128)


class UserUpdate(UserInput):
    password: str | None = Field(default=None, min_length=8, max_length=128)


class UserOutput(UserInput, ORMModel):
    id: UUID
    rol: RoleOutput


class TokenOutput(BaseModel):
    access_token: str
    token_type: str = "bearer"


class OrderLineInput(BaseModel):
    producto_id: UUID
    cantidad: int = Field(gt=0)


class OrderCreate(BaseModel):
    direccion_id: UUID
    productos: list[OrderLineInput] = Field(min_length=1)


class OrderLineOutput(ORMModel):
    producto_id: UUID
    codigo_producto: str
    nombre_producto: str
    precio_unitario: Decimal
    cantidad: int
    subtotal: Decimal


class OrderStateOutput(ORMModel):
    id: UUID
    nombre: str


class OrderCustomerOutput(ORMModel):
    id: UUID
    rut: str | None
    nombre: str | None
    celular: str | None


class OrderAddressOutput(ORMModel):
    id: UUID
    direccion: str
    comuna: str | None


class OrderOutput(ORMModel):
    id: UUID
    created_at: datetime
    cliente_id: UUID
    direccion_id: UUID
    estado_id: UUID
    estado: OrderStateOutput
    cliente: OrderCustomerOutput
    direccion: OrderAddressOutput
    subtotal: Decimal
    total: Decimal
    detalles: list[OrderLineOutput] = []


class OrderStatusUpdate(BaseModel):
    estado_id: UUID
    pagado: bool | None = None
    dias_credito: int | None = Field(default=None, ge=1, le=365)


class CreditCustomerOutput(ORMModel):
    id: UUID
    rut: str | None
    nombre: str | None
    celular: str | None


class CreditOrderOutput(ORMModel):
    id: UUID
    total: Decimal


class CreditOutput(ORMModel):
    id: UUID
    cliente_id: UUID
    pedido_id: UUID
    dias_credito: int
    fecha_entrega: datetime
    fecha_vencimiento: datetime
    pagado: bool
    fecha_pago: datetime | None
    cliente: CreditCustomerOutput
    pedido: CreditOrderOutput


class CreditPaymentInput(BaseModel):
    fecha_pago: date


class PedidoNotificacionLogOutput(ORMModel):
    id: UUID
    pedido_id: UUID | None = None
    canal: str
    tipo: str
    destinatario: str
    estado: str
    mensaje: str | None = None
    error: str | None = None
    duracion_ms: int | None = None
    created_at: datetime


class NotificationLogPage(BaseModel):
    items: list[PedidoNotificacionLogOutput]
    total: int
    page: int
    page_size: int


class NotificationLogStats(BaseModel):
    total: int
    whatsapp_enviados: int
    whatsapp_fallidos: int
    email_enviados: int
    email_fallidos: int
    omitidos: int


class PublicidadProductoOutput(ORMModel):
    id: UUID
    codigo: str
    nombre: str
    precio: Decimal
    precio_cliente: Decimal | None = None
    cantidad: int = 0
    imagen_url: str | None = None
    activo: bool = True


class PublicidadInput(BaseModel):
    producto_id: UUID | None = None
    titulo: str = Field(min_length=2, max_length=200)
    subtitulo: str | None = None
    etiqueta_1: str | None = Field(default=None, max_length=255)
    etiqueta_roja: str = Field(default="OFERTA", max_length=50)
    texto_boton: str = Field(default="Aprovechar Beneficio →", max_length=80)
    color_fondo: str = Field(default="#082620", max_length=60)
    orden: int = Field(default=0)


class PublicidadOutput(PublicidadInput, ORMModel):
    id: UUID
    producto: PublicidadProductoOutput | None = None
    created_at: datetime
    updated_at: datetime


