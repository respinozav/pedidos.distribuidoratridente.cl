from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.entities import (
    CarritoCompra,
    Cliente,
    Credito,
    DetallePedido,
    DetalleVentaVendedor,
    Direccion,
    Estado,
    Pedido,
    Producto,
    VentaVendedor,
)
from app.repositories.base import Repository
import logging

from app.services.defontana_service import DefontanaService, dispatch_defontana_order_sync_in_background
from app.services.notifications import _order_pdf, dispatch_order_notifications_in_background, notify_administrators_of_order
from app.services.pricing import customer_product_box_price, customer_product_price
from app.schemas.dto import OrderCreate, OrderUpdateAdmin

logger = logging.getLogger(__name__)


class OrderService:
    def __init__(self, database: Session):
        self.database = database

    def create(self, customer_id: UUID, payload: OrderCreate, vendedor_id: UUID | None = None) -> Pedido:
        customer = self.database.get(Cliente, customer_id)
        address = self.database.get(Direccion, payload.direccion_id)
        if not customer or not customer.activo or not address or address.cliente_id != customer_id or not address.activo:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Cliente o direccion invalida")

        product_ids = [line.producto_id for line in payload.productos]
        products = {
            product.id: product
            for product in self.database.scalars(
                select(Producto).options(selectinload(Producto.categoria)).where(Producto.id.in_(product_ids))
            )
        }
        if len(products) != len(set(product_ids)):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Uno o mas productos no existen")

        # Si el cliente tenía un carrito persistido en la base de datos, reintegrar el stock previamente reservado
        # para que la deducción de este pedido sea la única que descuente inventario de forma definitiva
        cart = self.database.scalar(
            select(CarritoCompra)
            .options(selectinload(CarritoCompra.items))
            .where(CarritoCompra.cliente_id == customer_id)
        )
        if cart:
            for item in cart.items:
                product_in_cart = products.get(item.producto_id)
                if not product_in_cart:
                    product_in_cart = self.database.scalar(
                        select(Producto).where(Producto.id == item.producto_id).with_for_update()
                    )
                if product_in_cart:
                    factor = (item.cantidad_caja or 1) if item.tipo_empaque == "caja" else 1
                    product_in_cart.cantidad += item.cantidad * factor
            self.database.delete(cart)

        details: list[DetallePedido] = []
        subtotal = Decimal("0")
        for line in payload.productos:
            product = products[line.producto_id]
            if not product.activo:
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"Producto inactivo: {product.codigo}")
            
            tipo_empaque = (line.tipo_empaque or "unidad").strip().lower()
            if tipo_empaque == "caja":
                applied_price = customer_product_box_price(product, customer)
                if applied_price is None:
                    applied_price = customer_product_price(product, customer)
                    tipo_empaque = "unidad"
                    cantidad_caja = None
                    unidades_descontar = line.cantidad
                else:
                    cantidad_caja = product.cantidad_caja or 1
                    unidades_descontar = line.cantidad * cantidad_caja
            else:
                applied_price = customer_product_price(product, customer)
                tipo_empaque = "unidad"
                cantidad_caja = None
                unidades_descontar = line.cantidad

            line_total = applied_price * line.cantidad
            product.cantidad -= unidades_descontar
            subtotal += line_total
            details.append(
                DetallePedido(
                    producto_id=product.id,
                    codigo_producto=product.codigo,
                    nombre_producto=product.nombre,
                    precio_unitario=applied_price,
                    cantidad=line.cantidad,
                    tipo_empaque=tipo_empaque,
                    cantidad_caja=cantidad_caja,
                    subtotal=line_total,
                )
            )


        initial_state = self.database.scalar(select(Estado).where(Estado.activo.is_(True)).order_by(Estado.created_at.asc()))
        if not initial_state:
            fallback_state = self.database.scalar(select(Estado).where(Estado.activo.is_(True)).order_by(Estado.id.asc()))
            if not fallback_state:
                fallback_state = Estado(nombre="Pedido", activo=True)
            initial_state = fallback_state
        if initial_state.nombre not in {"Pedido", "Pendiente", "Nuevo", "Por confirmar"}:
            fallback_state = self.database.scalar(
                select(Estado)
                .where(Estado.activo.is_(True))
                .order_by(Estado.created_at.asc())
            )
            if fallback_state:
                initial_state = fallback_state
        if not initial_state.id:
            self.database.add(initial_state)
            if hasattr(self.database, "flush"):
                self.database.flush()
        # Si no viene vendedor_id explícito (ej. el cliente realiza el pedido desde su portal),
        # se utiliza el vendedor asignado en su cartera para que reciba las comisiones
        effective_vendedor_id = vendedor_id or getattr(customer, "vendedor_id", None)

        order = Pedido(
            cliente_id=customer_id,
            direccion_id=address.id,
            estado_id=initial_state.id,
            subtotal=subtotal,
            total=subtotal,
            detalles=details,
            vendedor_id=effective_vendedor_id,
        )
        self.database.add(order)

        if effective_vendedor_id:
            detalles_venta: list[DetalleVentaVendedor] = []
            comision_acumulada = Decimal("0.00")
            for detail in details:
                prod = products.get(detail.producto_id)
                cat = prod.categoria if prod else None
                pct = Decimal(str(cat.comision_porcentaje or 0)) if cat else Decimal("0.00")
                monto = (detail.subtotal * (pct / Decimal("100"))).quantize(Decimal("0.01"))
                detalles_venta.append(
                    DetalleVentaVendedor(
                        producto_id=detail.producto_id,
                        categoria_id=cat.id if cat else None,
                        nombre_producto=detail.nombre_producto,
                        nombre_categoria=cat.nombre if cat else None,
                        cantidad=detail.cantidad,
                        precio_unitario=detail.precio_unitario,
                        subtotal=detail.subtotal,
                        comision_porcentaje=pct,
                        comision_monto=monto,
                    )
                )
                comision_acumulada += monto

            venta_vendedor = VentaVendedor(
                vendedor_id=effective_vendedor_id,
                pedido=order,
                cliente_id=customer_id,
                total_venta=subtotal,
                comision_total=comision_acumulada,
                detalles=detalles_venta,
            )
            self.database.add(venta_vendedor)

        self.database.commit()
        created_order = self.get(order.id)
        dispatch_order_notifications_in_background(created_order.id, tipo="NUEVO_PEDIDO")
        dispatch_defontana_order_sync_in_background(created_order.id)
        return created_order

    def update_admin(self, order_id: UUID, payload: OrderUpdateAdmin) -> Pedido:
        order = self.database.scalar(
            select(Pedido)
            .options(
                selectinload(Pedido.detalles),
                selectinload(Pedido.venta_vendedor),
                selectinload(Pedido.estado),
                selectinload(Pedido.cliente),
                selectinload(Pedido.direccion),
            )
            .where(Pedido.id == order_id)
        )
        if not order:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido no encontrado")
        
        estado_nombre = order.estado.nombre if order.estado else ""
        if estado_nombre in {"Despachado", "Entregado", "Cancelado"}:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"No se puede modificar un pedido en estado '{estado_nombre}'. Las restricciones de Defontana y despacho no permiten editar pedidos despachados, entregados o cancelados.",
            )

        customer = self.database.get(Cliente, order.cliente_id)

        # 1. Revertir stock de los detalles antiguos
        for item in order.detalles:
            prod = self.database.get(Producto, item.producto_id)
            if prod:
                factor = (item.cantidad_caja or 1) if item.tipo_empaque == "caja" else 1
                prod.cantidad += item.cantidad * factor

        # 2. Eliminar detalles antiguos y venta_vendedor antigua
        for item in list(order.detalles):
            self.database.delete(item)
        if order.venta_vendedor:
            self.database.delete(order.venta_vendedor)

        self.database.flush()

        # 3. Validar nuevos productos
        product_ids = [line.producto_id for line in payload.productos]
        products = {
            product.id: product
            for product in self.database.scalars(
                select(Producto).options(selectinload(Producto.categoria)).where(Producto.id.in_(product_ids))
            )
        }
        if len(products) != len(set(product_ids)):
            self.database.rollback()
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Uno o mas productos no existen")

        # 4. Calcular nuevos detalles, stock y subtotal
        details: list[DetallePedido] = []
        subtotal = Decimal("0")
        for line in payload.productos:
            product = products[line.producto_id]
            if not product.activo:
                self.database.rollback()
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"Producto inactivo: {product.codigo}")

            tipo_empaque = (line.tipo_empaque or "unidad").strip().lower()
            if tipo_empaque == "caja":
                applied_price = customer_product_box_price(product, customer)
                if applied_price is None:
                    applied_price = customer_product_price(product, customer)
                    tipo_empaque = "unidad"
                    cantidad_caja = None
                    unidades_descontar = line.cantidad
                else:
                    cantidad_caja = product.cantidad_caja or 1
                    unidades_descontar = line.cantidad * cantidad_caja
            else:
                applied_price = customer_product_price(product, customer)
                tipo_empaque = "unidad"
                cantidad_caja = None
                unidades_descontar = line.cantidad

            line_total = applied_price * line.cantidad
            product.cantidad -= unidades_descontar
            subtotal += line_total
            details.append(
                DetallePedido(
                    pedido_id=order.id,
                    producto_id=product.id,
                    codigo_producto=product.codigo,
                    nombre_producto=product.nombre,
                    precio_unitario=applied_price,
                    cantidad=line.cantidad,
                    tipo_empaque=tipo_empaque,
                    cantidad_caja=cantidad_caja,
                    subtotal=line_total,
                )
            )

        order.subtotal = subtotal
        order.total = subtotal
        if payload.direccion_id:
            order.direccion_id = payload.direccion_id
        
        # Guardar nuevos detalles
        self.database.add_all(details)

        # 5. Volver a generar VentaVendedor
        effective_vendedor_id = order.vendedor_id
        if effective_vendedor_id:
            detalles_venta: list[DetalleVentaVendedor] = []
            comision_acumulada = Decimal("0.00")
            for detail in details:
                prod = products.get(detail.producto_id)
                cat = prod.categoria if prod else None
                pct = Decimal(str(cat.comision_porcentaje or 0)) if cat else Decimal("0.00")
                monto = (detail.subtotal * (pct / Decimal("100"))).quantize(Decimal("0.01"))
                detalles_venta.append(
                    DetalleVentaVendedor(
                        producto_id=detail.producto_id,
                        categoria_id=cat.id if cat else None,
                        nombre_producto=detail.nombre_producto,
                        nombre_categoria=cat.nombre if cat else None,
                        cantidad=detail.cantidad,
                        precio_unitario=detail.precio_unitario,
                        subtotal=detail.subtotal,
                        comision_porcentaje=pct,
                        comision_monto=monto,
                    )
                )
                comision_acumulada += monto

            venta_vendedor = VentaVendedor(
                vendedor_id=effective_vendedor_id,
                pedido_id=order.id,
                cliente_id=order.cliente_id,
                total_venta=subtotal,
                comision_total=comision_acumulada,
                detalles=detalles_venta,
            )
            self.database.add(venta_vendedor)

        self.database.flush()

        # 6. Sincronizar y validar con Defontana antes de confirmar cambios en este sistema
        defontana_service = DefontanaService()
        if defontana_service.is_configured():
            _, defontana_err = defontana_service.sync_order(
                order.id,
                session=self.database,
                auto_commit=False,
                is_update=True,
            )
            if defontana_err:
                # Si Defontana no acepta el cambio, NO persistir el cambio en este sistema
                self.database.rollback()
                logger.warning(
                    "Defontana rechazó la modificación del pedido %s: %s",
                    order_id,
                    defontana_err,
                )
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    f"Defontana no aceptó la modificación del pedido: {defontana_err}",
                )

        # Si Defontana aceptó el cambio (o no está configurada), confirmar en base de datos
        self.database.commit()
        return self.get(order.id)


    def get(self, order_id: UUID) -> Pedido:
        order = self.database.scalar(select(Pedido).options(selectinload(Pedido.detalles).selectinload(DetallePedido.producto), selectinload(Pedido.estado), selectinload(Pedido.cliente), selectinload(Pedido.direccion)).where(Pedido.id == order_id))
        if not order:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido no encontrado")
        return order

    def pdf(self, order_id: UUID) -> bytes:
        return _order_pdf(self.get(order_id))

    def list_for_customer(self, customer_id: UUID, state_id: UUID | None = None) -> list[Pedido]:
        statement = select(Pedido).options(selectinload(Pedido.detalles).selectinload(DetallePedido.producto), selectinload(Pedido.estado), selectinload(Pedido.cliente), selectinload(Pedido.direccion)).where(Pedido.cliente_id == customer_id)
        if state_id:
            statement = statement.where(Pedido.estado_id == state_id)
        return list(self.database.scalars(statement.order_by(Pedido.created_at.desc())))

    def list_all(self) -> list[Pedido]:
        statement = select(Pedido).options(selectinload(Pedido.detalles).selectinload(DetallePedido.producto), selectinload(Pedido.estado), selectinload(Pedido.cliente), selectinload(Pedido.direccion))
        return list(self.database.scalars(statement.order_by(Pedido.created_at.desc())))

    def change_status(
        self,
        order_id: UUID,
        next_state_id: UUID,
        pagado: bool | None = None,
        dias_credito: int | None = None,
    ) -> Pedido:
        order = self.get(order_id)
        next_state = self.database.get(Estado, next_state_id)
        if not next_state or not next_state.activo:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Estado no disponible")
        transitions = {
            "Pedido": {"Despachado", "Cancelado"},
            "Pendiente": {"Despachado", "Cancelado"},
            "Nuevo": {"Despachado", "Cancelado"},
            "Despachado": {"Entregado", "Cancelado"},
        }
        current_state_name = order.estado.nombre if order.estado else "Pedido"
        allowed = transitions.get(current_state_name, set())
        if next_state.nombre not in allowed:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Transicion de estado no permitida")
        if next_state.nombre == "Entregado":
            if pagado is None:
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Indica si el cliente pagó el pedido")
            if not pagado and not dias_credito:
                if order.cliente and order.cliente.dias_credito and order.cliente.dias_credito > 0:
                    dias_credito = order.cliente.dias_credito
                else:
                    raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Indica los días de crédito")
            if not pagado and self.database.scalar(select(Credito.id).where(Credito.pedido_id == order.id)):
                raise HTTPException(status.HTTP_409_CONFLICT, "El pedido ya tiene un crédito registrado")
        order.estado_id = next_state.id
        if next_state.nombre == "Entregado" and not pagado:
            delivery_date = datetime.now(UTC)
            self.database.add(
                Credito(
                    cliente_id=order.cliente_id,
                    pedido_id=order.id,
                    dias_credito=dias_credito,
                    fecha_entrega=delivery_date,
                    fecha_vencimiento=delivery_date + timedelta(days=dias_credito),
                    pagado=False,
                )
            )
        self.database.commit()
        self.database.expire_all()
        return self.get(order.id)


class CustomerAccessService:
    def __init__(self, database: Session):
        self.database = database

    def authenticate(self, identifier: str) -> Cliente:
        identifier = identifier.strip()
        customer = self.database.scalar(
            select(Cliente).where(
                Cliente.activo.is_(True),
                or_(Cliente.rut == identifier, Cliente.celular == identifier, Cliente.nombre.ilike(identifier)),
            )
        )
        if not customer:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Cliente no autorizado")
        return customer