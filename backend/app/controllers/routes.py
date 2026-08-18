from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.api.dependencies import AdminUser, CustomerUser, DatabaseSession
from app.core.security import create_access_token, create_customer_access_token, hash_password, verify_password
from app.models.entities import Categoria, Cliente, Credito, Direccion, Estado, Pedido, PedidoNotificacionLog, Producto, Rol, Usuario
from app.repositories.base import Repository
from app.schemas.dto import (
    AddressInput,
    AddressOutput,
    CategoryInput,
    CategoryOutput,
    CreditOutput,
    CreditPaymentInput,
    CustomerCreate,
    CustomerInput,
    CustomerLogin,
    CustomerOutput,
    CustomerPasswordUpdate,
    CustomerProfileUpdate,
    CustomerUpdate,
    NotificationLogPage,
    NotificationLogStats,
    OrderCreate,
    OrderOutput,
    OrderStateOutput,
    OrderStatusUpdate,
    PedidoNotificacionLogOutput,
    ProductInput,
    ProductOutput,
    ProductPage,
    RoleOutput,
    TokenOutput,
    UserCreate,
    UserLogin,
    UserOutput,
    UserUpdate,
)
from app.api.endpoints.system_settings import router as system_settings_router
from app.api.endpoints.whatsapp import router as whatsapp_router
from app.services.notifications import dispatch_order_notifications_in_background, notify_customer_password_changed

from app.services.ordering import OrderService
from app.services.pricing import customer_product_price
from app.services.catalog import build_full_catalog_pdf, build_public_catalog_pdf, invalidate_catalog_cache

router = APIRouter(prefix="/api")
router.include_router(system_settings_router)
router.include_router(whatsapp_router)


@router.post("/login", response_model=TokenOutput, tags=["Autenticacion"])
def login(payload: UserLogin, database: DatabaseSession) -> TokenOutput:
    user = database.scalar(select(Usuario).where(Usuario.correo == payload.correo, Usuario.activo.is_(True)))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Credenciales invalidas")
    return TokenOutput(access_token=create_access_token(user.id, user.rol.nombre))


@router.get("/roles", response_model=list[RoleOutput], tags=["Usuarios"])
def list_roles(database: DatabaseSession, _: AdminUser) -> list[Rol]:
    return list(database.scalars(select(Rol).where(Rol.activo.is_(True)).order_by(Rol.nombre)))


@router.get("/usuarios", response_model=list[UserOutput], tags=["Usuarios"])
def list_users(database: DatabaseSession, _: AdminUser) -> list[Usuario]:
    statement = select(Usuario).options(selectinload(Usuario.rol)).order_by(Usuario.nombre)
    return list(database.scalars(statement))


@router.post("/usuarios", response_model=UserOutput, status_code=status.HTTP_201_CREATED, tags=["Usuarios"])
def create_user(payload: UserCreate, database: DatabaseSession, _: AdminUser) -> Usuario:
    role = database.get(Rol, payload.rol_id)
    if not role or not role.activo:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Rol no disponible")
    values = payload.model_dump(exclude={"password"})
    entity = Repository(Usuario, database).add(Usuario(**values, password_hash=hash_password(payload.password)))
    database.commit()
    database.refresh(entity, attribute_names=["rol"])
    return entity


@router.put("/usuarios/{user_id}", response_model=UserOutput, tags=["Usuarios"])
def update_user(user_id: UUID, payload: UserUpdate, database: DatabaseSession, current_user: AdminUser) -> Usuario:
    entity = Repository(Usuario, database).get(user_id)
    if not entity:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuario no encontrado")
    if entity.id == current_user.id and not payload.activo:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No puedes desactivar tu propio usuario")
    role = database.get(Rol, payload.rol_id)
    if not role or not role.activo:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Rol no disponible")
    values = payload.model_dump(exclude={"password"})
    if payload.password:
        values["password_hash"] = hash_password(payload.password)
    Repository(Usuario, database).update(entity, values)
    database.commit()
    database.refresh(entity, attribute_names=["rol"])
    return entity


@router.options("/clientes/login", tags=["Acceso cliente"])
def customer_login_options() -> None:
    return None


@router.post("/clientes/login", response_model=TokenOutput, tags=["Acceso cliente"])
def customer_login(payload: CustomerLogin, database: DatabaseSession) -> TokenOutput:
    customer = database.scalar(
        select(Cliente).where(Cliente.correo == payload.correo, Cliente.activo.is_(True))
    )
    if not customer or not customer.password_hash or not verify_password(payload.password, customer.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Credenciales invalidas")
    return TokenOutput(access_token=create_customer_access_token(customer.id))


@router.get("/cliente/perfil", response_model=CustomerOutput, tags=["Perfil cliente"])
def customer_profile(database: DatabaseSession, current_customer: CustomerUser) -> Cliente:
    return database.scalar(
        select(Cliente)
        .options(selectinload(Cliente.direcciones))
        .where(Cliente.id == current_customer.id)
    )


@router.put("/cliente/perfil", response_model=CustomerOutput, tags=["Perfil cliente"])
def update_customer_profile(
    payload: CustomerProfileUpdate,
    database: DatabaseSession,
    current_customer: CustomerUser,
) -> Cliente:
    current_customer.nombre = payload.nombre
    current_customer.celular = payload.celular
    database.commit()
    return customer_profile(database, current_customer)


@router.put("/cliente/perfil/clave", status_code=status.HTTP_204_NO_CONTENT, tags=["Perfil cliente"])
def update_customer_password(
    payload: CustomerPasswordUpdate,
    database: DatabaseSession,
    current_customer: CustomerUser,
) -> None:
    if not current_customer.password_hash or not verify_password(payload.current_password, current_customer.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "La contraseña actual es incorrecta")
    current_customer.password_hash = hash_password(payload.new_password)
    database.commit()
    notify_customer_password_changed(current_customer, database=database)


@router.post("/cliente/perfil/direcciones", response_model=AddressOutput, status_code=status.HTTP_201_CREATED, tags=["Perfil cliente"])
def add_customer_profile_address(
    payload: AddressInput,
    database: DatabaseSession,
    current_customer: CustomerUser,
) -> Direccion:
    addresses = list(database.scalars(select(Direccion).where(Direccion.cliente_id == current_customer.id)))
    values = payload.model_dump()
    if payload.principal or not any(address.principal and address.activo for address in addresses):
        for address in addresses:
            address.principal = False
        values.update(principal=True, activo=True)
    entity = Repository(Direccion, database).add(Direccion(cliente_id=current_customer.id, **values))
    database.commit()
    return entity


@router.put("/cliente/perfil/direcciones/{address_id}", response_model=AddressOutput, tags=["Perfil cliente"])
def update_customer_profile_address(
    address_id: UUID,
    payload: AddressInput,
    database: DatabaseSession,
    current_customer: CustomerUser,
) -> Direccion:
    address = database.get(Direccion, address_id)
    if not address or address.cliente_id != current_customer.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Direccion no encontrada")
    addresses = list(database.scalars(select(Direccion).where(Direccion.cliente_id == current_customer.id)))
    if payload.principal:
        for item in addresses:
            item.principal = item.id == address_id
        values = payload.model_dump()
        values.update(principal=True, activo=True)
    else:
        if address.principal and not any(item.id != address_id and item.principal and item.activo for item in addresses):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Debe existir una direccion principal activa")
        values = payload.model_dump()
    Repository(Direccion, database).update(address, values)
    database.commit()
    return address


@router.get("/categorias", response_model=list[CategoryOutput], tags=["Categorias"])
def list_categories(database: DatabaseSession, active_only: bool = True) -> list[Categoria]:
    statement = select(Categoria).where(Categoria.eliminado_at.is_(None))
    if active_only:
        statement = statement.where(Categoria.activo.is_(True))
    return list(database.scalars(statement.order_by(Categoria.nombre)))


@router.post("/categorias", response_model=CategoryOutput, status_code=status.HTTP_201_CREATED, tags=["Categorias"])
def create_category(payload: CategoryInput, database: DatabaseSession, _: AdminUser) -> Categoria:
    entity = Repository(Categoria, database).add(Categoria(**payload.model_dump()))
    database.commit()
    invalidate_catalog_cache()
    return entity


@router.put("/categorias/{category_id}", response_model=CategoryOutput, tags=["Categorias"])
def update_category(category_id: UUID, payload: CategoryInput, database: DatabaseSession, _: AdminUser) -> Categoria:
    entity = Repository(Categoria, database).get(category_id)
    if not entity or entity.eliminado_at:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Categoria no encontrada")
    Repository(Categoria, database).update(entity, payload.model_dump())
    database.commit()
    invalidate_catalog_cache()
    return entity


@router.delete("/categorias/{category_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Categorias"])
def delete_category(category_id: UUID, database: DatabaseSession, _: AdminUser) -> None:
    entity = Repository(Categoria, database).get(category_id)
    if not entity:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Categoria no encontrada")
    Repository(Categoria, database).soft_delete(entity)
    database.commit()
    invalidate_catalog_cache()


@router.get("/catalogo-publico", tags=["Catalogo publico"])
def public_catalog(database: DatabaseSession) -> Response:
    content = build_public_catalog_pdf(database)
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": 'inline; filename="catalogo-distribuidora-tridente.pdf"'},
    )


@router.get("/admin/catalogo/pdf", tags=["Catalogo admin"])
def full_catalog(database: DatabaseSession, _: AdminUser) -> Response:
    """Genera el Full Catalogo PDF (todas las categorias activas + precios) exclusivo para administradores."""
    content = build_full_catalog_pdf(database)
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": 'inline; filename="full-catalogo-tridente.pdf"'},
    )


@router.get("/productos", response_model=ProductPage, tags=["Productos"])
def list_products(
    database: DatabaseSession,
    category_id: UUID | None = None,
    search: str | None = Query(default=None, max_length=180),
    customer_id: UUID | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=10),
) -> ProductPage:
    statement = select(Producto).options(selectinload(Producto.categoria)).where(Producto.eliminado_at.is_(None), Producto.activo.is_(True))
    if category_id:
        statement = statement.where(Producto.categoria_id == category_id)
    if search:
        statement = statement.where(Producto.nombre.ilike(f"%{search}%"))
    customer = database.get(Cliente, customer_id) if customer_id else None
    total = database.scalar(select(func.count()).select_from(statement.subquery())) or 0
    products = database.scalars(statement.order_by(Producto.nombre).offset((page - 1) * page_size).limit(page_size))
    return ProductPage(
        items=[ProductOutput.model_validate(product, from_attributes=True).model_copy(update={"precio_cliente": customer_product_price(product, customer) if customer else None}) for product in products],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/admin/productos", response_model=ProductPage, tags=["Productos"])
def list_admin_products(
    database: DatabaseSession,
    _: AdminUser,
    category_id: UUID | None = None,
    search: str | None = Query(default=None, max_length=180),
    stock_lt: int | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=10),
) -> ProductPage:
    statement = select(Producto).where(Producto.eliminado_at.is_(None))
    if category_id:
        statement = statement.where(Producto.categoria_id == category_id)
    if search:
        statement = statement.where(Producto.nombre.ilike(f"%{search}%"))
    if stock_lt is not None:
        statement = statement.where(Producto.cantidad < stock_lt)
    total = database.scalar(select(func.count()).select_from(statement.subquery())) or 0
    products = database.scalars(statement.order_by(Producto.nombre).offset((page - 1) * page_size).limit(page_size))
    return ProductPage(items=list(products), total=total, page=page, page_size=page_size)


@router.post("/productos", response_model=ProductOutput, status_code=status.HTTP_201_CREATED, tags=["Productos"])
def create_product(payload: ProductInput, database: DatabaseSession, _: AdminUser) -> Producto:
    duplicate = database.scalar(select(Producto.id).where(func.lower(Producto.codigo) == payload.codigo.lower()))
    if duplicate:
        raise HTTPException(status.HTTP_409_CONFLICT, "El código de producto ya existe")
    entity = Repository(Producto, database).add(Producto(**payload.model_dump()))
    database.commit()
    invalidate_catalog_cache()
    return entity


@router.put("/productos/{product_id}", response_model=ProductOutput, tags=["Productos"])
def update_product(product_id: UUID, payload: ProductInput, database: DatabaseSession, _: AdminUser) -> Producto:
    entity = Repository(Producto, database).get(product_id)
    if not entity or entity.eliminado_at:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Producto no encontrado")
    duplicate = database.scalar(select(Producto.id).where(func.lower(Producto.codigo) == payload.codigo.lower(), Producto.id != product_id))
    if duplicate:
        raise HTTPException(status.HTTP_409_CONFLICT, "El código de producto ya existe")
    Repository(Producto, database).update(entity, payload.model_dump())
    database.commit()
    invalidate_catalog_cache()
    return entity


@router.get("/clientes", response_model=list[CustomerOutput], tags=["Clientes"])
def list_customers(database: DatabaseSession, _: AdminUser) -> list[Cliente]:
    return list(database.scalars(select(Cliente).options(selectinload(Cliente.direcciones)).where(Cliente.eliminado_at.is_(None))))


@router.post("/clientes", response_model=CustomerOutput, status_code=status.HTTP_201_CREATED, tags=["Clientes"])
def create_customer(payload: CustomerCreate, database: DatabaseSession, _: AdminUser) -> Cliente:
    values = payload.model_dump(exclude={"password"})
    entity = Repository(Cliente, database).add(Cliente(**values, password_hash=hash_password(payload.password)))
    database.commit()
    return entity


@router.put("/clientes/{customer_id}", response_model=CustomerOutput, tags=["Clientes"])
def update_customer(customer_id: UUID, payload: CustomerUpdate, database: DatabaseSession, _: AdminUser) -> Cliente:
    entity = Repository(Cliente, database).get(customer_id)
    if not entity or entity.eliminado_at:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cliente no encontrado")
    values = payload.model_dump(exclude={"password"})
    if payload.password:
        values["password_hash"] = hash_password(payload.password)
    Repository(Cliente, database).update(entity, values)
    database.commit()
    return entity


@router.post("/clientes/{customer_id}/direcciones", response_model=AddressOutput, status_code=status.HTTP_201_CREATED, tags=["Clientes"])
def add_address(customer_id: UUID, payload: AddressInput, database: DatabaseSession, _: AdminUser) -> Direccion:
    customer = database.get(Cliente, customer_id)
    if not customer or customer.eliminado_at:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cliente no encontrado")
    existing_addresses = list(database.scalars(select(Direccion).where(Direccion.cliente_id == customer_id)))
    values = payload.model_dump()
    if payload.principal or not any(address.principal and address.activo for address in existing_addresses):
        for address in existing_addresses:
            address.principal = False
        values["principal"] = True
        values["activo"] = True
    entity = Repository(Direccion, database).add(Direccion(cliente_id=customer_id, **values))
    database.commit()
    return entity


@router.put("/clientes/{customer_id}/direcciones/{address_id}", response_model=AddressOutput, tags=["Clientes"])
def update_address(
    customer_id: UUID,
    address_id: UUID,
    payload: AddressInput,
    database: DatabaseSession,
    _: AdminUser,
) -> Direccion:
    address = database.get(Direccion, address_id)
    if not address or address.cliente_id != customer_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Direccion no encontrada")
    addresses = list(database.scalars(select(Direccion).where(Direccion.cliente_id == customer_id)))
    if payload.principal:
        for item in addresses:
            item.principal = item.id == address_id
        payload_values = payload.model_dump()
        payload_values["activo"] = True
    else:
        if address.principal and not any(item.id != address_id and item.principal and item.activo for item in addresses):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Debe existir una direccion principal activa")
        payload_values = payload.model_dump()
    Repository(Direccion, database).update(address, payload_values)
    database.commit()
    return address


@router.post("/clientes/{customer_id}/pedidos", response_model=OrderOutput, status_code=status.HTTP_201_CREATED, tags=["Pedidos"])
def create_order(customer_id: UUID, payload: OrderCreate, database: DatabaseSession, current_customer: CustomerUser) -> object:
    if current_customer.id != customer_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No puedes crear pedidos para otro cliente")
    return OrderService(database).create(customer_id, payload)


@router.get("/clientes/{customer_id}/pedidos", response_model=list[OrderOutput], tags=["Pedidos"])
def customer_orders(customer_id: UUID, database: DatabaseSession, current_customer: CustomerUser, state_id: UUID | None = None) -> list[object]:
    if current_customer.id != customer_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No puedes consultar pedidos de otro cliente")
    return OrderService(database).list_for_customer(customer_id, state_id)


@router.get("/clientes/{customer_id}/pedidos/historicos", response_model=list[OrderOutput], tags=["Pedidos"])
def customer_order_history(customer_id: UUID, database: DatabaseSession, current_customer: CustomerUser) -> list[object]:
    if current_customer.id != customer_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No puedes consultar pedidos de otro cliente")
    return OrderService(database).list_for_customer(customer_id, None)


@router.get("/pedidos", response_model=list[OrderOutput], tags=["Pedidos"])
def list_orders(database: DatabaseSession, _: AdminUser) -> list[object]:
    return OrderService(database).list_all()


@router.get("/pedidos/{order_id}/pdf", tags=["Pedidos"])
def order_pdf(order_id: UUID, database: DatabaseSession, _: AdminUser) -> Response:
    content = OrderService(database).pdf(order_id)
    code = str(order_id).split("-")[0].upper()
    return Response(content=content, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="pedido-{code}.pdf"'})


@router.get("/creditos", response_model=list[CreditOutput], tags=["Créditos"])
def list_credits(database: DatabaseSession, _: AdminUser, pagado: bool = False) -> list[Credito]:
    statement = (
        select(Credito)
        .options(selectinload(Credito.cliente), selectinload(Credito.pedido))
        .where(Credito.pagado.is_(pagado))
        .order_by(Credito.fecha_vencimiento.desc())
    )
    return list(database.scalars(statement))


@router.patch("/creditos/{credit_id}/pago", response_model=CreditOutput, tags=["Créditos"])
def pay_credit(credit_id: UUID, payload: CreditPaymentInput, database: DatabaseSession, _: AdminUser) -> Credito:
    credit = database.scalar(
        select(Credito)
        .options(selectinload(Credito.cliente), selectinload(Credito.pedido))
        .where(Credito.id == credit_id)
    )
    if not credit:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Crédito no encontrado")
    if credit.pagado:
        raise HTTPException(status.HTTP_409_CONFLICT, "El crédito ya está pagado")
    credit.pagado = True
    credit.fecha_pago = datetime.combine(payload.fecha_pago, datetime.min.time(), tzinfo=UTC)
    database.commit()
    database.refresh(credit)
    return credit


@router.get("/estados", response_model=list[OrderStateOutput], tags=["Pedidos"])
def list_order_states(database: DatabaseSession, _: AdminUser) -> list[Estado]:
    return list(database.scalars(select(Estado).where(Estado.activo.is_(True)).order_by(Estado.nombre)))


@router.patch("/pedidos/{order_id}/estado", response_model=OrderOutput, tags=["Pedidos"])
def update_order_status(order_id: UUID, payload: OrderStatusUpdate, database: DatabaseSession, _: AdminUser) -> object:
    return OrderService(database).change_status(order_id, payload.estado_id, payload.pagado, payload.dias_credito)


@router.get("/admin/pedidos/logs", response_model=NotificationLogPage, tags=["Logs Notificaciones"])
def list_notification_logs(
    database: DatabaseSession,
    _: AdminUser,
    canal: str | None = None,
    estado: str | None = None,
    pedido_id: UUID | None = None,
    search: str | None = Query(default=None, max_length=150),
    desde: str | None = None,
    hasta: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> NotificationLogPage:
    """Lista los logs de notificaciones con filtros avanzados y paginación."""
    statement = select(PedidoNotificacionLog)
    if canal:
        statement = statement.where(PedidoNotificacionLog.canal == canal)
    if estado:
        statement = statement.where(PedidoNotificacionLog.estado == estado)
    if pedido_id:
        statement = statement.where(PedidoNotificacionLog.pedido_id == pedido_id)
    if search:
        search_pattern = f"%{search.strip()}%"
        statement = statement.where(
            (PedidoNotificacionLog.destinatario.ilike(search_pattern))
            | (PedidoNotificacionLog.mensaje.ilike(search_pattern))
            | (PedidoNotificacionLog.error.ilike(search_pattern))
        )
    if desde:
        try:
            from_dt = datetime.strptime(f"{desde} 00:00:00", "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)
            statement = statement.where(PedidoNotificacionLog.created_at >= from_dt)
        except ValueError:
            pass
    if hasta:
        try:
            to_dt = datetime.strptime(f"{hasta} 23:59:59", "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)
            statement = statement.where(PedidoNotificacionLog.created_at <= to_dt)
        except ValueError:
            pass

    total = database.scalar(select(func.count()).select_from(statement.subquery())) or 0
    logs = list(
        database.scalars(
            statement.order_by(PedidoNotificacionLog.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    return NotificationLogPage(
        items=[PedidoNotificacionLogOutput.model_validate(log, from_attributes=True) for log in logs],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/admin/pedidos/logs/stats", response_model=NotificationLogStats, tags=["Logs Notificaciones"])
def notification_logs_stats(database: DatabaseSession, _: AdminUser) -> NotificationLogStats:
    """Obtiene métricas rápidas de los logs de notificaciones."""
    total = database.scalar(select(func.count(PedidoNotificacionLog.id))) or 0
    whatsapp_enviados = (
        database.scalar(
            select(func.count(PedidoNotificacionLog.id)).where(
                PedidoNotificacionLog.canal == "WHATSAPP", PedidoNotificacionLog.estado == "ENVIADO"
            )
        )
        or 0
    )
    whatsapp_fallidos = (
        database.scalar(
            select(func.count(PedidoNotificacionLog.id)).where(
                PedidoNotificacionLog.canal == "WHATSAPP", PedidoNotificacionLog.estado == "FALLIDO"
            )
        )
        or 0
    )
    email_enviados = (
        database.scalar(
            select(func.count(PedidoNotificacionLog.id)).where(
                PedidoNotificacionLog.canal.in_(["EMAIL_ADMIN", "EMAIL_CLIENTE"]),
                PedidoNotificacionLog.estado == "ENVIADO",
            )
        )
        or 0
    )
    email_fallidos = (
        database.scalar(
            select(func.count(PedidoNotificacionLog.id)).where(
                PedidoNotificacionLog.canal.in_(["EMAIL_ADMIN", "EMAIL_CLIENTE"]),
                PedidoNotificacionLog.estado == "FALLIDO",
            )
        )
        or 0
    )
    omitidos = (
        database.scalar(
            select(func.count(PedidoNotificacionLog.id)).where(PedidoNotificacionLog.estado == "OMITIDO")
        )
        or 0
    )
    return NotificationLogStats(
        total=total,
        whatsapp_enviados=whatsapp_enviados,
        whatsapp_fallidos=whatsapp_fallidos,
        email_enviados=email_enviados,
        email_fallidos=email_fallidos,
        omitidos=omitidos,
    )


@router.get("/admin/pedidos/{order_id}/logs", response_model=list[PedidoNotificacionLogOutput], tags=["Logs Notificaciones"])
def order_notification_logs(order_id: UUID, database: DatabaseSession, _: AdminUser) -> list[PedidoNotificacionLog]:
    """Obtiene el historial de notificaciones de un pedido en particular."""
    return list(
        database.scalars(
            select(PedidoNotificacionLog)
            .where(PedidoNotificacionLog.pedido_id == order_id)
            .order_by(PedidoNotificacionLog.created_at.desc())
        )
    )


@router.post("/admin/pedidos/{order_id}/reintentar-notificaciones", tags=["Logs Notificaciones"])
def retry_order_notifications(order_id: UUID, database: DatabaseSession, _: AdminUser) -> dict[str, str]:
    """Reenvía en segundo plano las notificaciones (WhatsApp y Correo) de un pedido existente."""
    order = database.get(Pedido, order_id)
    if not order:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido no encontrado")
    dispatch_order_notifications_in_background(order_id, tipo="REINTENTO")
    return {"message": "Reintento de notificaciones iniciado en segundo plano"}