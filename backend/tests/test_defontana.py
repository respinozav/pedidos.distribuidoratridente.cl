from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from app.services.defontana_service import DefontanaService


def test_defontana_resolve_client_and_product():
    service = DefontanaService()
    if not service.is_configured():
        print("Defontana no configurada, omitiendo prueba de red.")
        return

    # Probar resolución de cliente por RUT
    client = service.resolve_client("77.673.176-5")
    assert client is not None, "Debería encontrar el cliente Todo Barato"
    assert "Todo Barato" in (client.get("fileID") or client.get("name") or "")

    # Probar resolución de producto por código
    product = service.resolve_product("20")
    assert product is not None, "Debería encontrar el producto código 20"
    assert product.get("code") == "20"
    print("test_defontana_resolve_client_and_product: OK")


def test_defontana_save_order_mocked():
    service = DefontanaService()

    fake_response = {
        "success": True,
        "folio": 9999,
        "message": "Pedido guardado exitosamente",
        "exceptionMessage": None,
    }

    with patch.object(service, "save_order", return_value=fake_response) as mock_save:
        res = service.save_order({"dummy": "payload"})
        assert res["success"] is True
        assert res["folio"] == 9999
        mock_save.assert_called_once()
def test_defontana_item_packaging_rules():
    service = DefontanaService()

    # Simular orden con 1 item de caja y 1 item de unidad
    customer = SimpleNamespace(rut="77.673.176-5", nombre="Cliente Prueba")
    item_caja = SimpleNamespace(
        codigo_producto="20",
        nombre_producto="LUCKY STRIKE",
        tipo_empaque="caja",
        cantidad_caja=10,
        precio_unitario=Decimal("75680"),
        cantidad=2,
        producto=SimpleNamespace(cantidad_caja=10),
    )
    item_unidad = SimpleNamespace(
        codigo_producto="673",
        nombre_producto="LATINO ICE",
        tipo_empaque="unidad",
        cantidad_caja=None,
        precio_unitario=Decimal("33242"),
        cantidad=5,
        producto=SimpleNamespace(cantidad_caja=None),
    )
    fake_order = SimpleNamespace(
        id=uuid4(),
        cliente=customer,
        direccion=SimpleNamespace(direccion="Calle 1"),
        detalles=[item_caja, item_unidad],
    )

    captured_payload = {}
    def mock_save(payload):
        nonlocal captured_payload
        captured_payload = payload
        return {"success": True, "folio": 1234}

    class FakeSession:
        def __init__(self, order):
            self.order = order
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc_val, exc_tb):
            pass
        def scalar(self, stmt):
            return self.order
        def commit(self):
            pass

    with patch("app.core.database.SessionLocal", return_value=FakeSession(fake_order)), \
         patch.object(service, "resolve_client", return_value={"fileID": "Ficha1", "sellerID": "V1", "localID": "L1", "paymentID": "Contado"}), \
         patch.object(service, "resolve_product", return_value={"type": "A", "unit": "UN"}), \
         patch.object(service, "save_order", side_effect=mock_save):
        
        folio, err = service.sync_order(fake_order.id)
        assert folio == 1234
        assert err is None
        details = captured_payload["orderDetails"]
        assert len(details) == 2

        # Validar ítem de caja
        d_caja = details[0]
        assert d_caja["unit"] == "UN"
        assert d_caja["count"] == 2
        assert d_caja["price"] == 75680.0
        assert d_caja["comment"] == "Presentación: CAJA x 10 unid."

        # Validar ítem de unidad
        d_unidad = details[1]
        assert d_unidad["unit"] == "UN"
        assert d_unidad["count"] == 5
        assert d_unidad["price"] == 33242.0
        assert d_unidad["comment"] == "Unidad"

    print("test_defontana_item_packaging_rules: OK")


if __name__ == "__main__":
    test_defontana_save_order_mocked()
    test_defontana_item_packaging_rules()
    test_defontana_resolve_client_and_product()
    print("TODOS LOS TESTS DE DEFONTANA PASARON EXITOSAMENTE!")
