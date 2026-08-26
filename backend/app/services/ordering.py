from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.entities import Cliente, Credito, DetallePedido, Direccion, Estado, Pedido, Producto
from app.repositories.base import Repository
from app.schemas.dto import OrderCreate
from app.services.notifications import _order_pdf, dispatch_order_notifications_in_background, notify_administrators_of_order
from app.services.pricing import customer_product_price


class OrderService:
    def __init__(self, database: Session):
        self.database = database

    def create(self, customer_id: UUID, payload: OrderCreate) -> Pedido:
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

        details: list[DetallePedido] = []
        subtotal = Decimal("0")
        for line in payload.productos:
            product = products[line.producto_id]
            if not product.activo:
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"Producto inactivo: {product.codigo}")
            applied_price = customer_product_price(product, customer)
            line_total = applied_price * line.cantidad
            product.cantidad -= line.cantidad
            subtotal += line_total
            details.append(DetallePedido(producto_id=product.id, codigo_producto=product.codigo, nombre_producto=product.nombre, precio_unitario=applied_price, cantidad=line.cantidad, subtotal=line_total))

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
        order = Pedido(cliente_id=customer_id, direccion_id=address.id, estado_id=initial_state.id, subtotal=subtotal, total=subtotal, detalles=details)
        self.database.add(order)
        self.database.commit()
        created_order = self.get(order.id)
        dispatch_order_notifications_in_background(created_order.id, tipo="NUEVO_PEDIDO")
        return created_order


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