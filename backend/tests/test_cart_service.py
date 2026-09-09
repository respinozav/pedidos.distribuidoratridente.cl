from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select
from app.models.entities import Categoria, Cliente, Producto, CarritoCompra, CarritoCompraItem
from app.models.system_settings import SystemSettings
from app.schemas.cart import CartItemInput
from app.services.cart_service import CartService


def _get_or_create_category(db_session):
    cat = db_session.scalar(select(Categoria).filter(Categoria.activo.is_(True)))
    if not cat:
        cat = Categoria(id=uuid4(), nombre="Cat Test", activo=True)
        db_session.add(cat)
        db_session.commit()
    return cat


def test_cart_service_reserve_and_return_stock(db_session):
    cat = _get_or_create_category(db_session)
    # 1. Crear producto con stock 10
    prod = Producto(
        id=uuid4(),
        categoria_id=cat.id,
        codigo=f"TEST-{uuid4().hex[:6]}",
        nombre="Producto Test Carro",
        precio=Decimal("1000.00"),
        cantidad=10,
        activo=True,
    )
    cliente = Cliente(
        id=uuid4(),
        rut="11111111-1",
        nombre="Cliente Test Carro",
        correo=f"test_{uuid4().hex[:6]}@test.cl",
        activo=True,
    )
    db_session.add_all([prod, cliente])
    db_session.commit()

    service = CartService(db_session)

    # 2. Agregar 3 unidades al carrito -> stock debe bajar a 7
    payload = CartItemInput(producto_id=prod.id, cantidad=3, tipo_empaque="unidad")
    cart_dto = service.add_or_update_item(cliente.id, payload)
    db_session.refresh(prod)

    assert cart_dto.total_items == 1
    assert cart_dto.total_unidades == 3
    assert prod.cantidad == 7

    # 3. Aumentar a 5 unidades -> stock debe bajar a 5
    payload2 = CartItemInput(producto_id=prod.id, cantidad=5, tipo_empaque="unidad")
    cart_dto = service.add_or_update_item(cliente.id, payload2)
    db_session.refresh(prod)

    assert cart_dto.total_unidades == 5
    assert prod.cantidad == 5

    # 4. Reducir a 2 unidades -> stock debe subir a 8
    payload3 = CartItemInput(producto_id=prod.id, cantidad=2, tipo_empaque="unidad")
    cart_dto = service.add_or_update_item(cliente.id, payload3)
    db_session.refresh(prod)

    assert cart_dto.total_unidades == 2
    assert prod.cantidad == 8

    # 5. Eliminar el ítem del carrito -> stock debe volver a 10
    item_id = cart_dto.items[0].id
    cart_dto = service.remove_item(cliente.id, item_id)
    db_session.refresh(prod)

    assert len(cart_dto.items) == 0
    assert prod.cantidad == 10


def test_cart_service_job_expiration(db_session):
    # 1. Configurar expiración en 2 horas
    settings = db_session.scalar(select(SystemSettings).filter(SystemSettings.id == 1))
    if not settings:
        settings = SystemSettings(id=1, carro_compras_expira_horas=2)
        db_session.add(settings)
    else:
        settings.carro_compras_expira_horas = 2
    db_session.commit()

    # 2. Crear producto y cliente
    cat = _get_or_create_category(db_session)
    prod = Producto(
        id=uuid4(),
        categoria_id=cat.id,
        codigo=f"EXP-{uuid4().hex[:6]}",
        nombre="Producto Expiracion Test",
        precio=Decimal("5000.00"),
        cantidad=20,
        activo=True,
    )
    cliente = Cliente(
        id=uuid4(),
        rut="22222222-2",
        nombre="Cliente Expirado",
        correo=f"exp_{uuid4().hex[:6]}@test.cl",
        activo=True,
    )
    db_session.add_all([prod, cliente])
    db_session.commit()

    service = CartService(db_session)
    service.add_or_update_item(cliente.id, CartItemInput(producto_id=prod.id, cantidad=4, tipo_empaque="unidad"))
    db_session.refresh(prod)
    assert prod.cantidad == 16

    # 3. Forzar updated_at del carrito a hace 3 horas (debe expirar)
    cart = db_session.scalar(select(CarritoCompra).where(CarritoCompra.cliente_id == cliente.id))
    assert cart is not None
    cart.updated_at = datetime.now(timezone.utc) - timedelta(hours=3)
    db_session.commit()

    # 4. Ejecutar job de expiración
    expirados = CartService.expire_inactive_carts(db_session)
    assert expirados >= 1

    # 5. Verificar que el carrito se eliminó y el stock regresó a 20
    db_session.refresh(prod)
    assert prod.cantidad == 20

    cart_post = db_session.scalar(select(CarritoCompra).where(CarritoCompra.cliente_id == cliente.id))
    assert cart_post is None
