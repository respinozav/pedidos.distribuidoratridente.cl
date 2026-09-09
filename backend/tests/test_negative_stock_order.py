from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select
from app.core.database import SessionLocal
from app.models.entities import Categoria, Cliente, Direccion, Estado, Pedido, Producto, CarritoCompra
from app.schemas.cart import CartItemInput
from app.schemas.dto import OrderCreate, OrderLineInput
from app.services.cart_service import CartService
from app.services.ordering import OrderService


def test_negative_stock_cart_and_order():
    db = SessionLocal()
    try:
        # 1. Obtener o crear categoría
        cat = db.scalar(select(Categoria).where(Categoria.activo.is_(True)))
        if not cat:
            cat = Categoria(id=uuid4(), nombre="Cat Test", activo=True)
            db.add(cat)
            db.commit()

        # 2. Crear producto con stock 0
        prod = Producto(
            id=uuid4(),
            categoria_id=cat.id,
            codigo=f"STK-0-{uuid4().hex[:6]}",
            nombre="Producto Stock Cero",
            precio=Decimal("1500.00"),
            cantidad=0,
            activo=True,
        )
        cliente = Cliente(
            id=uuid4(),
            rut=f"12{uuid4().int % 1000000:06d}-5",
            nombre="Cliente Prueba Stock Negativo",
            correo=f"test_neg_{uuid4().hex[:6]}@test.cl",
            activo=True,
        )
        db.add_all([prod, cliente])
        db.commit()

        direccion = Direccion(
            id=uuid4(),
            cliente_id=cliente.id,
            direccion="Calle Falsa 123",
            comuna="Santiago",
            principal=True,
            activo=True,
        )
        db.add(direccion)
        db.commit()

        # 3. Cliente agrega 2 unidades al carrito cuando el stock inicial es 0
        cart_service = CartService(db)
        cart_dto = cart_service.add_or_update_item(
            cliente.id,
            CartItemInput(producto_id=prod.id, cantidad=2, tipo_empaque="unidad"),
        )
        db.refresh(prod)

        assert cart_dto.total_items == 1
        assert cart_dto.total_unidades == 2
        # El stock debe haber pasado a -2 sin arrojar ninguna excepción
        assert prod.cantidad == -2, f"Esperado -2, obtenido {prod.cantidad}"

        # 4. Confirmar el pedido de esas 2 unidades
        order_service = OrderService(db)
        order_payload = OrderCreate(
            direccion_id=direccion.id,
            productos=[OrderLineInput(producto_id=prod.id, cantidad=2, tipo_empaque="unidad")],
        )
        order = order_service.create(cliente.id, order_payload)
        db.refresh(prod)

        # El pedido se crea correctamente y el stock final debe ser exactamente -2 (sin doble descuento)
        assert order is not None
        assert order.total == Decimal("3000.00")
        assert prod.cantidad == -2, f"Esperado -2 tras pedido, obtenido {prod.cantidad}"

        # El carrito debe haber sido limpiado
        cart_post = db.scalar(select(CarritoCompra).where(CarritoCompra.cliente_id == cliente.id))
        assert cart_post is None

        # 5. Nuevo pedido de 1 unidad más para el mismo producto (ahora stock pasa de -2 a -3)
        cart_dto2 = cart_service.add_or_update_item(
            cliente.id,
            CartItemInput(producto_id=prod.id, cantidad=1, tipo_empaque="unidad"),
        )
        db.refresh(prod)
        assert prod.cantidad == -3, f"Esperado -3 tras agregar al carro, obtenido {prod.cantidad}"

        order_payload2 = OrderCreate(
            direccion_id=direccion.id,
            productos=[OrderLineInput(producto_id=prod.id, cantidad=1, tipo_empaque="unidad")],
        )
        order2 = order_service.create(cliente.id, order_payload2)
        db.refresh(prod)
        assert order2 is not None
        assert prod.cantidad == -3, f"Esperado -3 tras segundo pedido, obtenido {prod.cantidad}"

        print("[OK] test_negative_stock_cart_and_order pasó exitosamente! Stock final:", prod.cantidad)

    finally:
        # Cleanup
        try:
            if 'cliente' in locals() and cliente.id:
                # eliminar ordenes y cliente de prueba
                for o in db.scalars(select(Pedido).where(Pedido.cliente_id == cliente.id)):
                    db.delete(o)
                for d in db.scalars(select(Direccion).where(Direccion.cliente_id == cliente.id)):
                    db.delete(d)
                db.delete(cliente)
            if 'prod' in locals() and prod.id:
                db.delete(prod)
            db.commit()
        except Exception:
            db.rollback()
        db.close()


if __name__ == "__main__":
    test_negative_stock_cart_and_order()
