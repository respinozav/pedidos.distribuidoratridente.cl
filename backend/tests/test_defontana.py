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
        producto=SimpleNamespace(afecto=True, cantidad_caja=10),
    )
    item_unidad = SimpleNamespace(
        codigo_producto="673",
        nombre_producto="LATINO ICE",
        tipo_empaque="unidad",
        cantidad_caja=None,
        precio_unitario=Decimal("33242"),
        cantidad=5,
        producto=SimpleNamespace(afecto=True, cantidad_caja=None),
    )
    fake_order = SimpleNamespace(
        id=uuid4(),
        cliente=customer,
        direccion=SimpleNamespace(direccion="Calle 1"),
        detalles=[item_caja, item_unidad],
        folio_defontana=None,
        folio_defontana_afecto=None,
        defontana_sincronizado=False,
        defontana_error=None,
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
        assert fake_order.folio_defontana_afecto == 1234
        assert fake_order.folio_defontana is None
        assert captured_payload["documentTypeId"] == "fvaelect"
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


def test_defontana_order_exclusively_afecto():
    service = DefontanaService()

    customer = SimpleNamespace(rut="77.673.176-5", nombre="Cliente Afecto")
    item1 = SimpleNamespace(
        codigo_producto="PROD-AFECTO-1",
        nombre_producto="Producto Afecto 1",
        tipo_empaque="unidad",
        cantidad_caja=None,
        precio_unitario=Decimal("10000"),
        cantidad=2,
        producto=SimpleNamespace(afecto=True, cantidad_caja=None),
    )
    item2 = SimpleNamespace(
        codigo_producto="PROD-AFECTO-2",
        nombre_producto="Producto Afecto 2",
        tipo_empaque="unidad",
        cantidad_caja=None,
        precio_unitario=Decimal("5000"),
        cantidad=3,
        producto=SimpleNamespace(afecto=True, cantidad_caja=None),
    )
    fake_order = SimpleNamespace(
        id=uuid4(),
        cliente=customer,
        direccion=SimpleNamespace(direccion="Calle 123"),
        detalles=[item1, item2],
        folio_defontana=None,
        folio_defontana_afecto=None,
        defontana_sincronizado=False,
        defontana_error=None,
    )

    captured_payload = {}

    def mock_save(payload):
        nonlocal captured_payload
        captured_payload = payload
        return {"success": True, "folio": 2001}

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

        def scalar(self, stmt):
            return fake_order

        def commit(self):
            pass

    with patch("app.core.database.SessionLocal", return_value=FakeSession()), \
         patch.object(service, "resolve_client", return_value={"fileID": "F1", "sellerID": "V1", "localID": "L1", "paymentID": "Contado"}), \
         patch.object(service, "resolve_product", return_value={"type": "A", "unit": "UN"}), \
         patch.object(service, "save_order", side_effect=mock_save):

        folio, err = service.sync_order(fake_order.id)
        assert folio == 2001
        assert err is None
        assert fake_order.folio_defontana_afecto == 2001
        assert fake_order.folio_defontana is None
        assert captured_payload["documentTypeId"] == "fvaelect"

        details = captured_payload["orderDetails"]
        assert len(details) == 2
        # Item 1: afecto
        assert details[0]["isExempt"] is False
        assert details[0]["tax"] == {"code": "IVA", "value": 19.0}
        assert details[0]["price"] == 10000.0
        assert details[0]["count"] == 2

        # Item 2: afecto
        assert details[1]["isExempt"] is False
        assert details[1]["tax"] == {"code": "IVA", "value": 19.0}
        assert details[1]["price"] == 5000.0
        assert details[1]["count"] == 3

        # Taxes: Total afecto = 10000*2 + 5000*3 = 35000. IVA = round(35000 * 0.19) = 6650.0
        taxes = captured_payload["taxes"]
        assert len(taxes) == 1
        assert taxes[0]["code"] == "IVA"
        assert taxes[0]["value"] == 6650.0

    print("test_defontana_order_exclusively_afecto: OK")


def test_defontana_order_exclusively_exento():
    service = DefontanaService()

    customer = SimpleNamespace(rut="77.673.176-5", nombre="Cliente Exento")
    item1 = SimpleNamespace(
        codigo_producto="PROD-EXENTO-1",
        nombre_producto="Producto Exento 1",
        tipo_empaque="unidad",
        cantidad_caja=None,
        precio_unitario=Decimal("12000"),
        cantidad=1,
        producto=SimpleNamespace(afecto=False, cantidad_caja=None),
    )
    item2 = SimpleNamespace(
        codigo_producto="PROD-EXENTO-2",
        nombre_producto="Producto Exento 2",
        tipo_empaque="unidad",
        cantidad_caja=None,
        precio_unitario=Decimal("8000"),
        cantidad=2,
        producto=SimpleNamespace(afecto=False, cantidad_caja=None),
    )
    fake_order = SimpleNamespace(
        id=uuid4(),
        cliente=customer,
        direccion=SimpleNamespace(direccion="Calle 456"),
        detalles=[item1, item2],
        folio_defontana=None,
        folio_defontana_afecto=None,
        defontana_sincronizado=False,
        defontana_error=None,
    )

    captured_payload = {}

    def mock_save(payload):
        nonlocal captured_payload
        captured_payload = payload
        return {"success": True, "folio": 2002}

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

        def scalar(self, stmt):
            return fake_order

        def commit(self):
            pass

    with patch("app.core.database.SessionLocal", return_value=FakeSession()), \
         patch.object(service, "resolve_client", return_value={"fileID": "F1", "sellerID": "V1", "localID": "L1", "paymentID": "Contado"}), \
         patch.object(service, "resolve_product", return_value={"type": "A", "unit": "UN"}), \
         patch.object(service, "save_order", side_effect=mock_save):

        folio, err = service.sync_order(fake_order.id)
        assert folio == 2002
        assert err is None
        assert fake_order.folio_defontana == 2002
        assert fake_order.folio_defontana_afecto is None
        assert captured_payload["documentTypeId"] == "fveelect"

        details = captured_payload["orderDetails"]
        assert len(details) == 2
        # Item 1: exento
        assert details[0]["isExempt"] is True
        assert details[0]["tax"] == {"code": "", "value": 0.0}

        # Item 2: exento
        assert details[1]["isExempt"] is True
        assert details[1]["tax"] == {"code": "", "value": 0.0}

        # Taxes: Factura 34 no lleva IVA en el header
        taxes = captured_payload["taxes"]
        assert len(taxes) == 0

    print("test_defontana_order_exclusively_exento: OK")


def test_defontana_order_mixed_afecto_and_exento():
    service = DefontanaService()

    fallback_prod_id = uuid4()
    db_product_fallback = SimpleNamespace(id=fallback_prod_id, afecto=True, cantidad_caja=None)

    customer = SimpleNamespace(rut="77.673.176-5", nombre="Cliente Mixto")
    # 1. Ítem afecto directo con producto cargado
    item1 = SimpleNamespace(
        codigo_producto="PROD-AFECTO",
        nombre_producto="Producto Afecto",
        tipo_empaque="unidad",
        cantidad_caja=None,
        precio_unitario=Decimal("20000"),
        cantidad=1,
        producto=SimpleNamespace(afecto=True, cantidad_caja=None),
    )
    # 2. Ítem exento directo
    item2 = SimpleNamespace(
        codigo_producto="PROD-EXENTO",
        nombre_producto="Producto Exento",
        tipo_empaque="unidad",
        cantidad_caja=None,
        precio_unitario=Decimal("15000"),
        cantidad=1,
        producto=SimpleNamespace(afecto=False, cantidad_caja=None),
    )
    # 3. Ítem afecto resuelto vía fallback de DB (session.get)
    item3 = SimpleNamespace(
        codigo_producto="PROD-FALLBACK",
        nombre_producto="Producto Fallback DB",
        tipo_empaque="unidad",
        cantidad_caja=None,
        precio_unitario=Decimal("10000"),
        cantidad=1,
        producto=None,
        producto_id=fallback_prod_id,
    )

    fake_order = SimpleNamespace(
        id=uuid4(),
        cliente=customer,
        direccion=SimpleNamespace(direccion="Calle 789"),
        detalles=[item1, item2, item3],
        folio_defontana=None,
        folio_defontana_afecto=None,
        defontana_sincronizado=False,
        defontana_error=None,
    )

    captured_payloads = []

    def mock_save(payload):
        captured_payloads.append(payload)
        doc_type = payload.get("documentTypeId")
        if doc_type == "fvaelect":
            return {"success": True, "folio": 3001}
        elif doc_type == "fveelect":
            return {"success": True, "folio": 3002}
        return {"success": True, "folio": 9999}

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

        def scalar(self, stmt):
            return fake_order

        def get(self, model, ident):
            if ident == fallback_prod_id:
                return db_product_fallback
            return None

        def commit(self):
            pass

    with patch("app.core.database.SessionLocal", return_value=FakeSession()), \
         patch.object(service, "resolve_client", return_value={"fileID": "F1", "sellerID": "V1", "localID": "L1", "paymentID": "Contado"}), \
         patch.object(service, "resolve_product", return_value={"type": "A", "unit": "UN"}), \
         patch.object(service, "save_order", side_effect=mock_save):

        folio, err = service.sync_order(fake_order.id)
        assert err is None
        assert fake_order.folio_defontana_afecto == 3001
        assert fake_order.folio_defontana == 3002
        assert fake_order.defontana_sincronizado is True
        assert len(captured_payloads) == 2

        # 1. Factura 33 (Afecta)
        p_afecto = next(p for p in captured_payloads if p["documentTypeId"] == "fvaelect")
        assert len(p_afecto["orderDetails"]) == 2  # item1 e item3
        assert p_afecto["orderDetails"][0]["isExempt"] is False
        assert p_afecto["orderDetails"][0]["tax"] == {"code": "IVA", "value": 19.0}
        assert p_afecto["orderDetails"][1]["isExempt"] is False
        assert p_afecto["orderDetails"][1]["tax"] == {"code": "IVA", "value": 19.0}
        # IVA = round((20000 + 10000) * 0.19) = 5700.0
        assert p_afecto["taxes"] == [{"code": "IVA", "value": 5700.0}]

        # 2. Factura 34 (Exenta)
        p_exento = next(p for p in captured_payloads if p["documentTypeId"] == "fveelect")
        assert len(p_exento["orderDetails"]) == 1  # item2
        assert p_exento["orderDetails"][0]["isExempt"] is True
        assert p_exento["orderDetails"][0]["tax"] == {"code": "", "value": 0.0}
        assert p_exento["taxes"] == []

    print("test_defontana_order_mixed_afecto_and_exento: OK")


def test_defontana_create_client_mocked():
    service = DefontanaService()

    cliente = SimpleNamespace(
        rut="11.222.333-4",
        nombre="Juan Perez Gonzalez",
        correo="juan.perez@example.com",
    )
    direccion = SimpleNamespace(
        direccion="Av. Siempre Viva 742",
        comuna="Providencia",
    )

    captured_req = {}

    class MockResponse:
        status_code = 200

        def json(self):
            return {"success": True, "message": "Cliente Guardado Exitosamente"}

        def raise_for_status(self):
            pass

    def mock_post(url, json=None, headers=None):
        nonlocal captured_req
        captured_req = {"url": url, "json": json, "headers": headers}
        return MockResponse()

    with patch("httpx.Client.post", side_effect=mock_post):
        result = service.create_client(cliente, direccion)

    assert result is not None
    assert result["success"] is True
    assert result["fileID"] == "11.222.333-4"
    assert result["legalCode"] == "11.222.333-4"
    assert result["name"] == "Juan Perez Gonzalez"

    payload = captured_req["json"]
    assert payload["legalCode"] == "11.222.333-4"
    assert payload["fileid"] == "11.222.333-4"
    assert payload["name"] == "Juan Perez Gonzalez"
    assert payload["address"] == "Av. Siempre Viva 742"
    assert payload["district"] == "Providencia"
    assert payload["city"] == "Providencia"
    assert payload["email"] == "juan.perez@example.com"
    assert payload["business"] == "Particular"
    assert payload["giro"] == "Particular"
    assert payload["rubroId"] == "1"

    print("test_defontana_create_client_mocked: OK")


def test_defontana_sync_order_creates_client_when_not_exists():
    service = DefontanaService()

    customer = SimpleNamespace(
        rut="99.888.777-6",
        nombre="Cliente Nuevo SpA",
        correo="contacto@clientenuevo.cl",
    )
    direccion = SimpleNamespace(
        direccion="Los Conquistadores 100",
        comuna="Las Condes",
    )
    item = SimpleNamespace(
        codigo_producto="20",
        nombre_producto="LUCKY STRIKE",
        tipo_empaque="unidad",
        cantidad_caja=None,
        precio_unitario=Decimal("5000"),
        cantidad=2,
        producto=SimpleNamespace(afecto=True, cantidad_caja=None),
    )
    fake_order = SimpleNamespace(
        id=uuid4(),
        cliente=customer,
        direccion=direccion,
        detalles=[item],
        folio_defontana=None,
        folio_defontana_afecto=None,
        defontana_sincronizado=False,
        defontana_error=None,
    )

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

        def scalar(self, stmt):
            return fake_order

        def commit(self):
            pass

    created_client_result = {
        "fileID": "99.888.777-6",
        "legalCode": "99.888.777-6",
        "name": "Cliente Nuevo SpA",
        "sellerID": "VENDEDOR",
        "localID": "Local",
        "paymentID": "Contado",
    }

    captured_payload = {}

    def mock_save(payload):
        nonlocal captured_payload
        captured_payload = payload
        return {"success": True, "folio": 8888}

    # En la 1ra búsqueda retorna None (no existe). Tras crearlo, retorna la ficha.
    resolve_calls = []

    def mock_resolve(rut):
        resolve_calls.append(rut)
        if len(resolve_calls) == 1:
            return None
        return created_client_result

    with patch("app.core.database.SessionLocal", return_value=FakeSession()), \
         patch.object(service, "resolve_client", side_effect=mock_resolve), \
         patch.object(service, "create_client", return_value=created_client_result) as mock_create, \
         patch.object(service, "resolve_product", return_value={"type": "A", "unit": "UN"}), \
         patch.object(service, "save_order", side_effect=mock_save):

        folio, err = service.sync_order(fake_order.id)
        assert folio == 8888
        assert err is None
        assert fake_order.folio_defontana_afecto == 8888
        mock_create.assert_called_once_with(customer, direccion)
        assert captured_payload["clientFileId"] == "99.888.777-6"
        assert len(resolve_calls) >= 2

    print("test_defontana_sync_order_creates_client_when_not_exists: OK")


if __name__ == "__main__":
    test_defontana_save_order_mocked()
    test_defontana_item_packaging_rules()
    test_defontana_resolve_client_and_product()
    test_defontana_order_exclusively_afecto()
    test_defontana_order_exclusively_exento()
    test_defontana_order_mixed_afecto_and_exento()
    test_defontana_create_client_mocked()
    test_defontana_sync_order_creates_client_when_not_exists()
    print("TODOS LOS TESTS DE DEFONTANA PASARON EXITOSAMENTE!")
