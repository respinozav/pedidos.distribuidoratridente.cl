from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

from app.schemas.dto import OrderCreate, OrderLineInput
from app.services.ordering import OrderService


class FakeSession:
    def __init__(self, customer, address, product, order=None):
        self.customer = customer
        self.address = address
        self.product = product
        self.order = order
        self.added = []
        self.deleted = []
        self.committed = False
        self.rolled_back = False

    def get(self, model, identifier):
        model_name = getattr(model, "__name__", str(model))
        if model_name == "Cliente":
            return self.customer
        if model_name == "Direccion":
            return self.address
        if model_name == "Producto":
            return self.product
        if model_name == "Estado":
            return None
        return None

    def scalar(self, statement):
        return self.order

    def scalars(self, statement):
        return [self.product]

    def add(self, instance):
        self.added.append(instance)
        if hasattr(instance, "id") and instance.id is None:
            instance.id = uuid4()

    def add_all(self, instances):
        self.added.extend(instances)

    def delete(self, instance):
        self.deleted.append(instance)

    def flush(self):
        return None

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True


def test_create_creates_default_state_when_none_exists(monkeypatch):
    customer = SimpleNamespace(id=uuid4(), activo=True, porcentaje=Decimal("0"))
    address = SimpleNamespace(id=uuid4(), cliente_id=customer.id, activo=True)
    product = SimpleNamespace(
        id=uuid4(),
        activo=True,
        codigo="PR-001",
        nombre="Producto de prueba",
        precio=Decimal("1000"),
        cantidad=10,
        categoria=SimpleNamespace(id=uuid4(), nombre="Cat", comision_porcentaje=Decimal("0"), usa_porcentaje_cliente=True, porcentaje=Decimal("0")),
    )
    session = FakeSession(customer, address, product)

    dispatched = []
    defontana_dispatched = []
    monkeypatch.setattr("app.services.ordering.customer_product_price", lambda product, customer: Decimal("1000"))
    monkeypatch.setattr("app.services.ordering.dispatch_order_notifications_in_background", lambda order_id, tipo="NUEVO_PEDIDO": dispatched.append((order_id, tipo)))
    monkeypatch.setattr("app.services.ordering.dispatch_defontana_order_sync_in_background", lambda order_id: defontana_dispatched.append(order_id))
    monkeypatch.setattr(OrderService, "get", lambda self, order_id: self.database.added[-1])

    service = OrderService(session)
    payload = OrderCreate(
        direccion_id=address.id,
        productos=[OrderLineInput(producto_id=product.id, cantidad=1)],
    )

    order = service.create(customer.id, payload)

    assert order is not None
    assert session.committed is True
    assert any(getattr(item, "nombre", None) == "Pedido" for item in session.added)
    assert len(dispatched) == 1
    assert dispatched[0][0] == order.id
    assert len(defontana_dispatched) == 1
    assert defontana_dispatched[0] == order.id


def test_update_admin_rejects_on_terminal_state(monkeypatch):
    from fastapi import HTTPException
    from app.schemas.dto import OrderUpdateAdmin

    customer = SimpleNamespace(id=uuid4(), activo=True)
    product = SimpleNamespace(id=uuid4(), activo=True, cantidad=10)
    order = SimpleNamespace(
        id=uuid4(),
        cliente_id=customer.id,
        estado=SimpleNamespace(nombre="Despachado"),
        detalles=[],
        venta_vendedor=None,
    )
    session = FakeSession(customer, None, product, order=order)
    service = OrderService(session)

    payload = OrderUpdateAdmin(
        productos=[OrderLineInput(producto_id=product.id, cantidad=2)],
    )

    try:
        service.update_admin(order.id, payload)
        assert False, "Debería haber lanzado HTTPException por estado Despachado"
    except HTTPException as exc:
        assert exc.status_code == 400
        assert "Despachado" in exc.detail
        assert session.committed is False


def test_update_admin_rolls_back_when_defontana_rejects(monkeypatch):
    from fastapi import HTTPException
    from app.schemas.dto import OrderUpdateAdmin

    customer = SimpleNamespace(id=uuid4(), activo=True, vendedor_id=None)
    product = SimpleNamespace(
        id=uuid4(),
        activo=True,
        codigo="PR-001",
        nombre="Producto A",
        precio=Decimal("2000"),
        cantidad=10,
        categoria=SimpleNamespace(id=uuid4(), nombre="Cat", comision_porcentaje=Decimal("5.0")),
    )
    old_detail = SimpleNamespace(
        producto_id=product.id,
        cantidad=2,
        tipo_empaque="unidad",
        cantidad_caja=None,
    )
    order = SimpleNamespace(
        id=uuid4(),
        cliente_id=customer.id,
        vendedor_id=None,
        estado=SimpleNamespace(nombre="Pendiente"),
        detalles=[old_detail],
        venta_vendedor=None,
        subtotal=Decimal("4000"),
        total=Decimal("4000"),
        direccion_id=None,
    )
    session = FakeSession(customer, None, product, order=order)

    rejection_msg = "La orden no se puede modificar porque ya tiene factura emitida (DTE 33)"

    from app.services.defontana_service import DefontanaService
    monkeypatch.setattr("app.services.ordering.customer_product_price", lambda p, c: Decimal("2000"))
    monkeypatch.setattr("app.services.ordering.customer_product_box_price", lambda p, c: None)
    monkeypatch.setattr(DefontanaService, "is_configured", lambda self: True)
    monkeypatch.setattr(
        DefontanaService,
        "sync_order",
        lambda self, order_id, session=None, auto_commit=True, is_update=False: (None, rejection_msg),
    )

    service = OrderService(session)
    payload = OrderUpdateAdmin(
        productos=[OrderLineInput(producto_id=product.id, cantidad=3)],
    )

    try:
        service.update_admin(order.id, payload)
        assert False, "Debería haber lanzado HTTPException"
    except HTTPException as exc:
        assert exc.status_code == 400
        assert "Defontana no aceptó la modificación" in exc.detail
        assert rejection_msg in exc.detail
        assert session.rolled_back is True
        assert session.committed is False


def test_update_admin_commits_when_defontana_accepts(monkeypatch):
    from app.schemas.dto import OrderUpdateAdmin
    from app.services.defontana_service import DefontanaService

    customer = SimpleNamespace(id=uuid4(), activo=True, vendedor_id=None)
    product = SimpleNamespace(
        id=uuid4(),
        activo=True,
        codigo="PR-001",
        nombre="Producto A",
        precio=Decimal("2000"),
        cantidad=10,
        categoria=SimpleNamespace(id=uuid4(), nombre="Cat", comision_porcentaje=Decimal("5.0")),
    )
    old_detail = SimpleNamespace(
        producto_id=product.id,
        cantidad=2,
        tipo_empaque="unidad",
        cantidad_caja=None,
    )
    order = SimpleNamespace(
        id=uuid4(),
        cliente_id=customer.id,
        vendedor_id=None,
        estado=SimpleNamespace(nombre="Pendiente"),
        detalles=[old_detail],
        venta_vendedor=None,
        subtotal=Decimal("4000"),
        total=Decimal("4000"),
        direccion_id=None,
    )
    session = FakeSession(customer, None, product, order=order)

    monkeypatch.setattr("app.services.ordering.customer_product_price", lambda p, c: Decimal("2000"))
    monkeypatch.setattr("app.services.ordering.customer_product_box_price", lambda p, c: None)
    monkeypatch.setattr(DefontanaService, "is_configured", lambda self: True)
    monkeypatch.setattr(
        DefontanaService,
        "sync_order",
        lambda self, order_id, session=None, auto_commit=True, is_update=False: (1234, None),
    )
    monkeypatch.setattr(OrderService, "get", lambda self, order_id: order)

    service = OrderService(session)
    payload = OrderUpdateAdmin(
        productos=[OrderLineInput(producto_id=product.id, cantidad=3)],
    )

    result = service.update_admin(order.id, payload)
    assert result is not None
    assert session.committed is True
    assert session.rolled_back is False
    assert order.total == Decimal("6000")

