import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class AuditMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)


class Rol(AuditMixin, Base):
    __tablename__ = "roles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nombre: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    usuarios: Mapped[list["Usuario"]] = relationship(back_populates="rol")


class Estado(AuditMixin, Base):
    __tablename__ = "estados"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nombre: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    pedidos: Mapped[list["Pedido"]] = relationship(back_populates="estado")


class Usuario(AuditMixin, Base):
    __tablename__ = "usuarios"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nombre: Mapped[str] = mapped_column(String(150))
    correo: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    rol_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("roles.id"), index=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    celular: Mapped[str | None] = mapped_column(String(30), nullable=True)
    recibe_pedido: Mapped[bool] = mapped_column(Boolean, default=False)
    rol: Mapped[Rol] = relationship(back_populates="usuarios")


class Categoria(AuditMixin, Base):
    __tablename__ = "categorias"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nombre: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    orden: Mapped[int] = mapped_column(Integer, default=0)
    usa_porcentaje_cliente: Mapped[bool] = mapped_column(Boolean, default=True)
    porcentaje: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    en_catalogo_publico: Mapped[bool] = mapped_column(Boolean, default=True)
    eliminado_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    productos: Mapped[list["Producto"]] = relationship(back_populates="categoria")


class Producto(AuditMixin, Base):
    __tablename__ = "productos"
    __table_args__ = (Index("ix_productos_nombre_activo", "nombre", "activo"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    categoria_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("categorias.id"), index=True)
    codigo: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    nombre: Mapped[str] = mapped_column(String(180), index=True)
    precio: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    cantidad: Mapped[int] = mapped_column(default=0)
    imagen_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    eliminado_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    categoria: Mapped[Categoria] = relationship(back_populates="productos")


class Cliente(AuditMixin, Base):
    __tablename__ = "clientes"
    __table_args__ = (Index("ix_clientes_nombre_activo", "nombre", "activo"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rut: Mapped[str | None] = mapped_column(String(20), index=True, nullable=True)
    nombre: Mapped[str | None] = mapped_column(String(180), nullable=True)
    celular: Mapped[str | None] = mapped_column(String(30), unique=True, index=True, nullable=True)
    correo: Mapped[str | None] = mapped_column(String(255), unique=True, index=True, nullable=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    porcentaje: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    eliminado_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    direcciones: Mapped[list["Direccion"]] = relationship(back_populates="cliente")
    pedidos: Mapped[list["Pedido"]] = relationship(back_populates="cliente")
    creditos: Mapped[list["Credito"]] = relationship(back_populates="cliente")


class Direccion(AuditMixin, Base):
    __tablename__ = "direcciones"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cliente_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clientes.id"), index=True)
    direccion: Mapped[str] = mapped_column(Text)
    comuna: Mapped[str | None] = mapped_column(String(100), nullable=True)
    principal: Mapped[bool] = mapped_column(Boolean, default=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    cliente: Mapped[Cliente] = relationship(back_populates="direcciones")


class Pedido(AuditMixin, Base):
    __tablename__ = "pedidos"
    __table_args__ = (Index("ix_pedidos_cliente_estado", "cliente_id", "estado_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cliente_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clientes.id"), index=True)
    direccion_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("direcciones.id"))
    estado_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("estados.id"), index=True)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    cliente: Mapped[Cliente] = relationship(back_populates="pedidos")
    direccion: Mapped[Direccion] = relationship()
    estado: Mapped[Estado] = relationship(back_populates="pedidos")
    detalles: Mapped[list["DetallePedido"]] = relationship(back_populates="pedido", cascade="all, delete-orphan")
    credito: Mapped["Credito | None"] = relationship(back_populates="pedido", uselist=False)
    notificaciones_logs: Mapped[list["PedidoNotificacionLog"]] = relationship(
        back_populates="pedido", cascade="all, delete-orphan", order_by="PedidoNotificacionLog.created_at.desc()"
    )


class Credito(AuditMixin, Base):
    __tablename__ = "creditos"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cliente_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clientes.id"), index=True)
    pedido_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("pedidos.id"), unique=True, index=True)
    dias_credito: Mapped[int] = mapped_column()
    fecha_entrega: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    fecha_vencimiento: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    pagado: Mapped[bool] = mapped_column(Boolean, default=False)
    fecha_pago: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cliente: Mapped[Cliente] = relationship(back_populates="creditos")
    pedido: Mapped[Pedido] = relationship(back_populates="credito")


class DetallePedido(AuditMixin, Base):
    __tablename__ = "detalle_pedidos"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pedido_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("pedidos.id"), index=True)
    producto_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("productos.id"))
    codigo_producto: Mapped[str] = mapped_column(String(50))
    nombre_producto: Mapped[str] = mapped_column(String(180))
    precio_unitario: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    cantidad: Mapped[int] = mapped_column()
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    pedido: Mapped[Pedido] = relationship(back_populates="detalles")


class PedidoNotificacionLog(AuditMixin, Base):
    __tablename__ = "pedido_notificacion_logs"
    __table_args__ = (
        Index("ix_pedido_notificacion_logs_pedido_id", "pedido_id"),
        Index("ix_pedido_notificacion_logs_canal_estado", "canal", "estado"),
        Index("ix_pedido_notificacion_logs_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pedido_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("pedidos.id", ondelete="CASCADE"), nullable=True, index=True
    )
    canal: Mapped[str] = mapped_column(String(30))  # "WHATSAPP", "EMAIL_ADMIN", "EMAIL_CLIENTE", "SISTEMA"
    tipo: Mapped[str] = mapped_column(String(50))  # "NUEVO_PEDIDO", "REINTENTO", "CAMBIO_ESTADO"
    destinatario: Mapped[str] = mapped_column(String(255))
    estado: Mapped[str] = mapped_column(String(30))  # "ENVIADO", "FALLIDO", "OMITIDO"
    mensaje: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    duracion_ms: Mapped[int | None] = mapped_column(nullable=True)
    pedido: Mapped[Pedido | None] = relationship(back_populates="notificaciones_logs")


class Publicidad(AuditMixin, Base):
    __tablename__ = "publicidades"
    __table_args__ = (
        Index("ix_publicidades_orden", "orden"),
        Index("ix_publicidades_producto_id", "producto_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    producto_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("productos.id", ondelete="SET NULL"), nullable=True, index=True
    )
    titulo: Mapped[str] = mapped_column(String(200))
    subtitulo: Mapped[str | None] = mapped_column(Text, nullable=True)
    etiqueta_1: Mapped[str | None] = mapped_column(String(255), nullable=True)
    etiqueta_roja: Mapped[str] = mapped_column(String(50), default="OFERTA")
    texto_boton: Mapped[str] = mapped_column(String(80), default="Aprovechar Beneficio →")
    color_fondo: Mapped[str] = mapped_column(String(60), default="#082620")
    orden: Mapped[int] = mapped_column(Integer, default=0)

    producto: Mapped[Producto | None] = relationship("Producto")


