from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

from app.schemas.dto import OrderCreate, OrderLineInput
from app.services.ordering import OrderService


class FakeSession:
    def __init__(self, customer, address, product):
        self.customer = customer
        self.address = address
        self.product = product
        self.added = []
        self.committed = False

    def get(self, model, identifier):
        model_name = getattr(model, "__name__", str(model))
        if model_name == "Cliente":
            return self.customer
        if model_name == "Direccion":
            return self.address
        if model_name == "Estado":
            return None
        return None

    def scalar(self, statement):
        return None

    def scalars(self, statement):
        return [self.product]

    def add(self, instance):
        self.added.append(instance)
        if hasattr(instance, "id") and instance.id is None:
            instance.id = uuid4()

    def flush(self):
        return None

    def commit(self):
        self.committed = True


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
        categoria=SimpleNamespace(usa_porcentaje_cliente=True, porcentaje=Decimal("0")),
    )
    session = FakeSession(customer, address, product)

    dispatched = []
    monkeypatch.setattr("app.services.ordering.customer_product_price", lambda product, customer: Decimal("1000"))
    monkeypatch.setattr("app.services.ordering.dispatch_order_notifications_in_background", lambda order_id, tipo="NUEVO_PEDIDO": dispatched.append((order_id, tipo)))
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

