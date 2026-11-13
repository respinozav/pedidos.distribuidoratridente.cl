from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
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

    def expire(self, instance, attribute_names=None):
        pass


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


def test_update_admin_passes_updated_details_and_is_update_flag(monkeypatch):
    """
    Simula el caso real: Pedido #5856 con 1 unidad a $5.313 se edita a 2 unidades ($10.626).
    Verifica que:
    1. order.detalles se actualiza en memoria con cantidad 2 y subtotal $10.626.
    2. defontana_service.sync_order se llama con is_update=True.
    3. sync_order ve la lista order.detalles con la nueva cantidad.
    """
    from app.schemas.dto import OrderUpdateAdmin
    from app.services.defontana_service import DefontanaService

    customer = SimpleNamespace(id=uuid4(), activo=True, vendedor_id=None)
    product = SimpleNamespace(
        id=uuid4(),
        activo=True,
        codigo="PROD-5856",
        nombre="Producto Caso Real",
        precio=Decimal("5313"),
        cantidad=10,
        categoria=SimpleNamespace(id=uuid4(), nombre="General", comision_porcentaje=Decimal("0")),
    )
    old_detail = SimpleNamespace(
        producto_id=product.id,
        cantidad=1,
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
        subtotal=Decimal("5313"),
        total=Decimal("5313"),
        direccion_id=None,
        folio_defontana_afecto=5856,
        folio_defontana=None,
    )
    session = FakeSession(customer, None, product, order=order)

    sync_calls = []

    def mock_sync_order(self_svc, order_id, session=None, auto_commit=True, is_update=False):
        # Verificar qué ve sync_order en order.detalles en el momento de la llamada
        detalles_visibles = list(order.detalles)
        sync_calls.append({
            "order_id": order_id,
            "is_update": is_update,
            "detalles_count": len(detalles_visibles),
            "cantidad_primer_item": detalles_visibles[0].cantidad if detalles_visibles else None,
            "subtotal_primer_item": detalles_visibles[0].subtotal if detalles_visibles else None,
        })
        return (5856, None)

    monkeypatch.setattr("app.services.ordering.customer_product_price", lambda p, c: Decimal("5313"))
    monkeypatch.setattr("app.services.ordering.customer_product_box_price", lambda p, c: None)
    monkeypatch.setattr(DefontanaService, "is_configured", lambda self: True)
    monkeypatch.setattr(DefontanaService, "sync_order", mock_sync_order)
    monkeypatch.setattr(OrderService, "get", lambda self, order_id: order)

    service = OrderService(session)
    payload = OrderUpdateAdmin(
        productos=[OrderLineInput(producto_id=product.id, cantidad=2)],
    )

    result = service.update_admin(order.id, payload)
    assert result is not None
    assert session.committed is True
    assert order.total == Decimal("10626")

    # Validar que sync_order recibió is_update=True y los detalles actualizados con cantidad 2
    assert len(sync_calls) == 1
    call = sync_calls[0]
    assert call["is_update"] is True
    assert call["detalles_count"] == 1
    assert call["cantidad_primer_item"] == 2
    assert call["subtotal_primer_item"] == Decimal("10626")


if __name__ == "__main__":
    class MonkeyPatch:
        def __init__(self):
            self._setattrs = []
        def setattr(self, target, name_or_value, value=None):
            if value is None:
                mod_name, attr_name = target.rsplit(".", 1)
                import importlib
                mod = importlib.import_module(mod_name)
                val = name_or_value
                old_val = getattr(mod, attr_name)
                setattr(mod, attr_name, val)
                self._setattrs.append((mod, attr_name, old_val))
            else:
                old_val = getattr(target, name_or_value)
                setattr(target, name_or_value, value)
                self._setattrs.append((target, name_or_value, old_val))
        def undo(self):
            for target, name, old_val in reversed(self._setattrs):
                setattr(target, name, old_val)

    mp = MonkeyPatch()
    try:
        test_create_creates_default_state_when_none_exists(mp)
        test_update_admin_rejects_on_terminal_state(mp)
        test_update_admin_rolls_back_when_defontana_rejects(mp)
        test_update_admin_commits_when_defontana_accepts(mp)
        test_update_admin_passes_updated_details_and_is_update_flag(mp)
        print("TODOS LOS TESTS DE ORDERING PASARON EXITOSAMENTE!")
    finally:
        mp.undo()

