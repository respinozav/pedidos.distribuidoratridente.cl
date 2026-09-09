import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.entities import Cliente, Direccion, Producto, CarritoCompra, CarritoCompraItem
from app.models.system_settings import SystemSettings
from app.schemas.cart import (
    AdminActiveCartOutput,
    AdminCartItemOutput,
    CartItemInput,
    CartItemOutput,
    CartOutput,
)
from app.services.pricing import customer_product_box_price, customer_product_price

logger = logging.getLogger(__name__)


class CartService:
    def __init__(self, database: Session):
        self.database = database

    def _get_expire_hours(self) -> int:
        settings = self.database.scalar(select(SystemSettings).filter(SystemSettings.id == 1))
        if settings and settings.carro_compras_expira_horas:
            return max(1, settings.carro_compras_expira_horas)
        return 24

    def get_or_create_cart(self, customer_id: UUID) -> CarritoCompra:
        cart = self.database.scalar(
            select(CarritoCompra)
            .options(
                selectinload(CarritoCompra.items).selectinload(CarritoCompraItem.producto),
                selectinload(CarritoCompra.cliente),
            )
            .where(CarritoCompra.cliente_id == customer_id)
        )
        if not cart:
            cart = CarritoCompra(cliente_id=customer_id)
            self.database.add(cart)
            self.database.commit()
            self.database.refresh(cart)
            # Volver a cargar con relaciones
            cart = self.database.scalar(
                select(CarritoCompra)
                .options(
                    selectinload(CarritoCompra.items).selectinload(CarritoCompraItem.producto),
                    selectinload(CarritoCompra.cliente),
                )
                .where(CarritoCompra.id == cart.id)
            )
        return cart

    def get_cart_dto(self, customer_id: UUID) -> CartOutput:
        cart = self.get_or_create_cart(customer_id)
        items_dto: list[CartItemOutput] = []
        total_items = 0
        total_unidades = 0
        total_monto = Decimal("0.00")

        for item in cart.items:
            prod = item.producto
            if not prod:
                continue
            unidades = item.cantidad * (item.cantidad_caja or 1) if item.tipo_empaque == "caja" else item.cantidad
            total_items += 1
            total_unidades += unidades
            total_monto += item.subtotal

            items_dto.append(
                CartItemOutput(
                    id=item.id,
                    producto_id=item.producto_id,
                    codigo_producto=prod.codigo,
                    nombre_producto=prod.nombre,
                    imagen_url=prod.imagen_url,
                    cantidad=item.cantidad,
                    tipo_empaque=item.tipo_empaque,
                    cantidad_caja=item.cantidad_caja,
                    precio_unitario=item.precio_unitario,
                    subtotal=item.subtotal,
                    stock_actual=prod.cantidad,
                )
            )

        return CartOutput(
            id=cart.id,
            cliente_id=cart.cliente_id,
            direccion_id=cart.direccion_id,
            items=items_dto,
            total_items=total_items,
            total_unidades=total_unidades,
            total=total_monto,
            created_at=cart.created_at,
            updated_at=cart.updated_at,
        )

    def add_or_update_item(self, customer_id: UUID, payload: CartItemInput) -> CartOutput:
        customer = self.database.get(Cliente, customer_id)
        if not customer or not customer.activo:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Cliente inválido o inactivo")

        # Bloquear fila del producto para actualizar stock de forma segura
        product = self.database.scalar(
            select(Producto).where(Producto.id == payload.producto_id).with_for_update()
        )
        if not product or product.eliminado_at or not product.activo:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Producto no disponible")

        cart = self.get_or_create_cart(customer_id)
        tipo_empaque = (payload.tipo_empaque or "unidad").strip().lower()

        # Determinar precio y unidades por empaque
        if tipo_empaque == "caja":
            applied_price = customer_product_box_price(product, customer)
            if applied_price is None:
                applied_price = customer_product_price(product, customer)
                tipo_empaque = "unidad"
                cantidad_caja = None
                factor = 1
            else:
                cantidad_caja = product.cantidad_caja or 1
                factor = cantidad_caja
        else:
            applied_price = customer_product_price(product, customer)
            tipo_empaque = "unidad"
            cantidad_caja = None
            factor = 1

        # Buscar si ya existe la línea en el carrito
        existing_item = next(
            (i for i in cart.items if i.producto_id == product.id and i.tipo_empaque == tipo_empaque),
            None,
        )

        cantidad_anterior = existing_item.cantidad if existing_item else 0
        diferencia_cant = payload.cantidad - cantidad_anterior
        unidades_necesarias = diferencia_cant * factor

        if unidades_necesarias > 0:
            # Necesitamos descontar más stock
            if product.cantidad < unidades_necesarias:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    f"Stock insuficiente para {product.nombre}. Disponible: {product.cantidad} unidades.",
                )
            product.cantidad -= unidades_necesarias
        elif unidades_necesarias < 0:
            # Devolver stock
            product.cantidad += abs(unidades_necesarias)

        subtotal = applied_price * payload.cantidad

        if existing_item:
            existing_item.cantidad = payload.cantidad
            existing_item.precio_unitario = applied_price
            existing_item.subtotal = subtotal
            existing_item.cantidad_caja = cantidad_caja
            existing_item.updated_at = datetime.now(UTC)
        else:
            new_item = CarritoCompraItem(
                carrito_id=cart.id,
                producto_id=product.id,
                cantidad=payload.cantidad,
                tipo_empaque=tipo_empaque,
                cantidad_caja=cantidad_caja,
                precio_unitario=applied_price,
                subtotal=subtotal,
            )
            self.database.add(new_item)

        cart.updated_at = datetime.now(UTC)
        self.database.commit()
        return self.get_cart_dto(customer_id)

    def remove_item(self, customer_id: UUID, item_id: UUID) -> CartOutput:
        cart = self.get_or_create_cart(customer_id)
        item = next((i for i in cart.items if i.id == item_id), None)
        if not item:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Ítem no encontrado en el carrito")

        # Bloquear producto para reintegrar stock
        product = self.database.scalar(
            select(Producto).where(Producto.id == item.producto_id).with_for_update()
        )
        if product:
            factor = (item.cantidad_caja or 1) if item.tipo_empaque == "caja" else 1
            unidades_a_devolver = item.cantidad * factor
            product.cantidad += unidades_a_devolver

        self.database.delete(item)
        cart.updated_at = datetime.now(UTC)
        self.database.commit()
        return self.get_cart_dto(customer_id)

    def clear_cart(self, customer_id: UUID) -> None:
        cart = self.database.scalar(
            select(CarritoCompra)
            .options(selectinload(CarritoCompra.items))
            .where(CarritoCompra.cliente_id == customer_id)
        )
        if not cart:
            return

        for item in cart.items:
            product = self.database.scalar(
                select(Producto).where(Producto.id == item.producto_id).with_for_update()
            )
            if product:
                factor = (item.cantidad_caja or 1) if item.tipo_empaque == "caja" else 1
                unidades_a_devolver = item.cantidad * factor
                product.cantidad += unidades_a_devolver

        self.database.delete(cart)
        self.database.commit()

    def list_active_carts(self) -> list[AdminActiveCartOutput]:
        expire_hours = self._get_expire_hours()
        now = datetime.now(UTC)

        carts = list(
            self.database.scalars(
                select(CarritoCompra)
                .options(
                    selectinload(CarritoCompra.cliente),
                    selectinload(CarritoCompra.items).selectinload(CarritoCompraItem.producto),
                )
                .order_by(CarritoCompra.updated_at.desc())
            )
        )

        result: list[AdminActiveCartOutput] = []
        for cart in carts:
            if not cart.items:
                continue
            customer = cart.cliente
            if not customer:
                continue

            # Calcular tiempo restante
            # cart.updated_at puede tener timezone o no
            updated_dt = cart.updated_at
            if updated_dt.tzinfo is None:
                updated_dt = updated_dt.replace(tzinfo=UTC)

            expire_limit = updated_dt + timedelta(hours=expire_hours)
            diff_seconds = int((expire_limit - now).total_seconds())
            expirado = diff_seconds <= 0

            admin_items: list[AdminCartItemOutput] = []
            total_unidades = 0
            total_monto = Decimal("0.00")

            for item in cart.items:
                prod = item.producto
                factor = (item.cantidad_caja or 1) if item.tipo_empaque == "caja" else 1
                unidades = item.cantidad * factor
                total_unidades += unidades
                total_monto += item.subtotal

                admin_items.append(
                    AdminCartItemOutput(
                        id=item.id,
                        producto_id=item.producto_id,
                        codigo_producto=prod.codigo if prod else "N/A",
                        nombre_producto=prod.nombre if prod else "Producto eliminado",
                        cantidad=item.cantidad,
                        tipo_empaque=item.tipo_empaque,
                        cantidad_caja=item.cantidad_caja,
                        unidades_totales=unidades,
                        precio_unitario=item.precio_unitario,
                        subtotal=item.subtotal,
                    )
                )

            result.append(
                AdminActiveCartOutput(
                    id=cart.id,
                    cliente_id=cart.cliente_id,
                    cliente_rut=customer.rut,
                    cliente_nombre=customer.nombre or "Sin nombre",
                    cliente_correo=customer.correo,
                    cliente_celular=customer.celular,
                    created_at=cart.created_at,
                    updated_at=cart.updated_at,
                    total_items=len(cart.items),
                    total_unidades=total_unidades,
                    total=total_monto,
                    expira_en_segundos=max(0, diff_seconds),
                    expirado=expirado,
                    items=admin_items,
                )
            )

        return result

    def admin_delete_cart(self, cart_id: UUID) -> dict[str, str]:
        cart = self.database.scalar(
            select(CarritoCompra)
            .options(selectinload(CarritoCompra.items))
            .where(CarritoCompra.id == cart_id)
        )
        if not cart:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Carro de compras no encontrado")

        total_devuelto = 0
        for item in cart.items:
            product = self.database.scalar(
                select(Producto).where(Producto.id == item.producto_id).with_for_update()
            )
            if product:
                factor = (item.cantidad_caja or 1) if item.tipo_empaque == "caja" else 1
                unidades_a_devolver = item.cantidad * factor
                product.cantidad += unidades_a_devolver
                total_devuelto += unidades_a_devolver

        self.database.delete(cart)
        self.database.commit()
        return {
            "status": "success",
            "message": f"Carro de compras eliminado exitosamente. Se devolvieron {total_devuelto} unidades al stock.",
        }

    @classmethod
    def expire_inactive_carts(cls, db: Session) -> int:
        """
        Job para liberar stock de carritos inactivos que superaron las X horas configuradas.
        """
        settings = db.scalar(select(SystemSettings).filter(SystemSettings.id == 1))
        expire_hours = (
            max(1, settings.carro_compras_expira_horas)
            if settings and settings.carro_compras_expira_horas
            else 24
        )

        limite = datetime.now(UTC) - timedelta(hours=expire_hours)

        expired_carts = list(
            db.scalars(
                select(CarritoCompra)
                .options(selectinload(CarritoCompra.items))
                .where(CarritoCompra.updated_at < limite)
            )
        )

        if not expired_carts:
            return 0

        logger.info(
            "Limpieza de carros: Se encontraron %s carritos expirados (inactivos por más de %s horas)",
            len(expired_carts),
            expire_hours,
        )

        count = 0
        for cart in expired_carts:
            try:
                for item in cart.items:
                    product = db.scalar(
                        select(Producto).where(Producto.id == item.producto_id).with_for_update()
                    )
                    if product:
                        factor = (item.cantidad_caja or 1) if item.tipo_empaque == "caja" else 1
                        product.cantidad += item.cantidad * factor

                db.delete(cart)
                db.commit()
                count += 1
            except Exception as e:
                db.rollback()
                logger.error("Error al expirar carrito %s: %s", cart.id, e)

        return count
