from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
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

    try:
        service.get_token()
    except Exception as exc:
        print(f"Credenciales de Defontana no operativas ({exc}), omitiendo prueba de red.")
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
         patch.object(service, "update_client", return_value={"success": True}), \
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
         patch.object(service, "update_client", return_value={"success": True}), \
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
         patch.object(service, "update_client", return_value={"success": True}), \
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
        # Item 1: exento (Factura 34 no debe llevar 'Unidad' como comentario)
        assert details[0]["isExempt"] is True
        assert details[0]["tax"] == {"code": "", "value": 0.0}
        assert details[0]["comment"] == ""

        # Item 2: exento (Factura 34 no debe llevar 'Unidad' como comentario)
        assert details[1]["isExempt"] is True
        assert details[1]["tax"] == {"code": "", "value": 0.0}
        assert details[1]["comment"] == ""

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
         patch.object(service, "update_client", return_value={"success": True}), \
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
        assert p_exento["orderDetails"][0]["comment"] == ""
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

    with patch("httpx.Client.post", side_effect=mock_post), \
         patch.object(service, "get_token", return_value="fake-token"):
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


def test_defontana_sync_product_existing():
    service = DefontanaService()
    existing_product_data = {
        "code": "44",
        "name": "Encendedor Ronson Clearlite Transparente",
        "unit": "UN",
        "categoryID": 10,
        "sellPrice": 3700.0,
        "priceListDetail": [
            {"priceListID": 1, "unitPrice": 3700.0},
            {"priceListID": 2, "unitPrice": 3700.0},
        ],
    }

    updated_payload = {}
    price_list_updates = []

    def mock_update(payload):
        nonlocal updated_payload
        updated_payload = payload
        return {"success": True, "message": "Producto actualizado"}

    def mock_save_pl(pl_id, code, price):
        price_list_updates.append((pl_id, code, price))
        return {"success": True}

    with patch.object(service, "resolve_product", return_value=existing_product_data), \
         patch.object(service, "update_product_defontana", side_effect=mock_update) as mock_upd, \
         patch.object(service, "save_product_price_list", side_effect=mock_save_pl):

        ok, err = service.sync_product(
            code="44",
            name="ENCENDEDOR RONSON CLEARLITE TRANSPARENTE",
            price=Decimal("3701.00"),
            category_name="ABARROTES",
        )
        assert ok is True
        assert err is None
        assert updated_payload["code"] == "44"
        assert updated_payload["price"] == 3701.0
        assert updated_payload["unit"] == "UN"
        assert len(price_list_updates) == 2
        assert price_list_updates[0] == (1, "44", 3701.0)
        assert price_list_updates[1] == (2, "44", 3701.0)

    print("test_defontana_sync_product_existing: OK")


def test_defontana_sync_product_new():
    service = DefontanaService()
    saved_payload = {}

    def mock_save(payload):
        nonlocal saved_payload
        saved_payload = payload
        return {"success": True, "message": "Producto creado"}

    with patch.object(service, "resolve_product", return_value=None), \
         patch.object(service, "save_product", side_effect=mock_save), \
         patch.object(service, "get_categories", return_value=[{"categoryID": 12, "description": "ABARROTES"}]):

        ok, err = service.sync_product(
            code="999",
            name="PRODUCTO NUEVO",
            price=Decimal("1500.00"),
            category_name="ABARROTES",
        )
        assert ok is True
        assert err is None
        assert saved_payload["code"] == "999"
        assert saved_payload["price"] == 1500.0
        assert saved_payload["categoryID"] == 12

    print("test_defontana_sync_product_new: OK")


def test_defontana_update_client_mocked():
    service = DefontanaService()

    cliente = SimpleNamespace(
        rut="77.673.176-5",
        nombre="Cliente Tridente SpA",
        correo="contacto@tridente.cl",
        celular="+56911223344",
    )
    direccion = SimpleNamespace(
        direccion="Av. Providencia 1234, Of 501",
        comuna="Providencia",
    )
    existing_client_data = {
        "fileID": "77.673.176-5",
        "name": "Cliente Tridente SpA",
        "business": "Comercializadora",
        "giro": "Venta al por mayor",
        "rubroId": "1",
    }

    captured_req = {}

    class MockResponse:
        status_code = 200

        def json(self):
            return {"success": True, "message": "Cliente Actualizado Exitosamente"}

        def raise_for_status(self):
            pass

    def mock_post(url, json=None, headers=None):
        nonlocal captured_req
        captured_req = {"url": url, "json": json, "headers": headers}
        return MockResponse()

    with patch("httpx.Client.post", side_effect=mock_post), \
         patch.object(service, "get_token", return_value="fake-token"):
        result = service.update_client(cliente, direccion, client_data=existing_client_data)

    assert result is not None
    assert result["success"] is True

    payload = captured_req["json"]
    assert "/api/Sale/UpdateClient" in captured_req["url"]
    assert payload["legalCode"] == "77.673.176-5"
    assert payload["fileid"] == "77.673.176-5"
    assert payload["name"] == "Cliente Tridente SpA"
    assert payload["address"] == "Av. Providencia 1234, Of 501"
    assert payload["district"] == "Providencia"
    assert payload["city"] == "Providencia"
    assert payload["email"] == "contacto@tridente.cl"
    assert payload["phone"] == "+56911223344"
    assert payload["business"] == "Comercializadora"
    assert payload["giro"] == "Venta al por mayor"
    assert payload["rubroId"] == "1"

    print("test_defontana_update_client_mocked: OK")


def test_defontana_sync_order_propagates_selected_address_to_payload_and_client():
    service = DefontanaService()

    customer = SimpleNamespace(
        rut="77.673.176-5",
        nombre="Distribuidora Cliente",
        correo="pedidos@cliente.cl",
        celular="+56999887766",
    )
    selected_address = SimpleNamespace(
        direccion="Camino La Montaña 100, Bodega 4",
        comuna="Lampa",
    )
    item = SimpleNamespace(
        codigo_producto="20",
        nombre_producto="LUCKY STRIKE",
        tipo_empaque="unidad",
        cantidad_caja=None,
        precio_unitario=Decimal("5000"),
        cantidad=1,
        producto=SimpleNamespace(afecto=True, cantidad_caja=None),
    )
    fake_order = SimpleNamespace(
        id=uuid4(),
        cliente=customer,
        direccion=selected_address,
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

    client_data_in_defontana = {
        "fileID": "77.673.176-5",
        "legalCode": "77.673.176-5",
        "name": "Distribuidora Cliente",
        "sellerID": "V01",
        "localID": "CasaMatriz",
        "paymentID": "30Dias",
    }

    captured_payload = {}
    def mock_save(payload):
        nonlocal captured_payload
        captured_payload = payload
        return {"success": True, "folio": 5555}

    update_client_called = {}
    def mock_update_client(cliente, direccion, client_data=None):
        update_client_called["cliente"] = cliente
        update_client_called["direccion"] = direccion
        update_client_called["client_data"] = client_data
        return {"success": True}

    with patch("app.core.database.SessionLocal", return_value=FakeSession()), \
         patch.object(service, "resolve_client", return_value=client_data_in_defontana), \
         patch.object(service, "update_client", side_effect=mock_update_client), \
         patch.object(service, "resolve_product", return_value={"type": "A", "unit": "UN"}), \
         patch.object(service, "save_order", side_effect=mock_save):

        folio, err = service.sync_order(fake_order.id)
        assert folio == 5555
        assert err is None
        assert fake_order.defontana_sincronizado is True

        # 1. Verifica que update_client fue invocado con la dirección seleccionada
        assert update_client_called["cliente"] == customer
        assert update_client_called["direccion"] == selected_address
        assert update_client_called["direccion"].direccion == "Camino La Montaña 100, Bodega 4"
        assert update_client_called["direccion"].comuna == "Lampa"

        # 2. Verifica que el payload de la orden en Defontana incluye todos los campos de despacho
        assert captured_payload["district"] == "Lampa"
        assert captured_payload["address"] == "Camino La Montaña 100, Bodega 4"
        assert captured_payload["deliveryAddress"] == "Camino La Montaña 100, Bodega 4"
        assert captured_payload["city"] == "Lampa"
        assert captured_payload["glossDispatch"] == "Despacho: Camino La Montaña 100, Bodega 4, Lampa"
        assert "Despacho: Camino La Montaña 100, Bodega 4, Lampa" in captured_payload["glossGeneral"]
        assert "Despacho: Camino La Montaña 100, Bodega 4, Lampa" in captured_payload["glossBill"]

    print("test_defontana_sync_order_propagates_selected_address_to_payload_and_client: OK")



def test_defontana_sync_order_updates_when_address_differs_from_defontana():
    """
    Caso Cliente con Dirección Nueva:
    El cliente ya existe en Defontana con 'Calle 1, Santiago'.
    El cliente hace un pedido seleccionando 'Calle 2, Providencia'.
    Validar que update_client es ejecutado para registrar 'Calle 2' en Defontana antes de emitir la factura.
    """
    service = DefontanaService()

    customer = SimpleNamespace(
        rut="77.673.176-5",
        nombre="Cliente Prueba",
        correo="prueba@cliente.cl",
        celular="+56911223344",
    )
    # Dirección 2 seleccionada
    selected_address = SimpleNamespace(
        direccion="Calle 2",
        comuna="Providencia",
        ciudad="Santiago",
    )
    item = SimpleNamespace(
        codigo_producto="100",
        nombre_producto="BEBIDA COCA COLA",
        tipo_empaque="unidad",
        cantidad_caja=None,
        precio_unitario=Decimal("1500"),
        cantidad=10,
        producto=SimpleNamespace(afecto=True, cantidad_caja=None),
    )
    fake_order = SimpleNamespace(
        id=uuid4(),
        cliente=customer,
        direccion=selected_address,
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

    # Cliente existe en Defontana pero solo tiene Calle 1 registrada
    client_in_defontana = {
        "fileID": "77.673.176-5",
        "legalCode": "77.673.176-5",
        "name": "Cliente Prueba",
        "address": "Calle 1",
        "district": "Santiago",
        "city": "Santiago",
        "sellerID": "V01",
        "localID": "CasaMatriz",
        "paymentID": "Contado",
    }

    captured_payload = {}
    def mock_save(payload):
        nonlocal captured_payload
        captured_payload = payload
        return {"success": True, "folio": 9999}

    update_client_calls = []
    def mock_update_client(cliente, direccion, client_data=None):
        update_client_calls.append({"cliente": cliente, "direccion": direccion, "client_data": client_data})
        return {"success": True}

    with patch("app.core.database.SessionLocal", return_value=FakeSession()), \
         patch.object(service, "resolve_client", return_value=client_in_defontana), \
         patch.object(service, "update_client", side_effect=mock_update_client), \
         patch.object(service, "resolve_product", return_value={"type": "A", "unit": "UN"}), \
         patch.object(service, "save_order", side_effect=mock_save):

        folio, err = service.sync_order(fake_order.id)
        assert folio == 9999
        assert err is None
        assert fake_order.defontana_sincronizado is True

        # Validar que update_client fue invocado porque la dirección del pedido (Calle 2)
        # no coincidía con la que tenía Defontana (Calle 1)
        assert len(update_client_calls) >= 1
        last_call = update_client_calls[0]
        assert last_call["cliente"].rut == "77.673.176-5"
        assert last_call["direccion"].direccion == "Calle 2"
        assert last_call["direccion"].comuna == "Providencia"

        # Validar que la orden se envió con la Dirección 2
        assert captured_payload["address"] == "Calle 2"
        assert captured_payload["district"] == "Providencia"
        assert captured_payload["city"] == "Santiago"
        assert "Calle 2, Providencia" in captured_payload["glossDispatch"]

    print("test_defontana_sync_order_updates_when_address_differs_from_defontana: OK")


def test_defontana_sync_order_reactive_retry_on_address_error():
    """
    Caso Reintento por Error de Dirección:
    Simula que save_order retorna un error de dirección o sucursal no encontrada en Defontana.
    El mecanismo de reintento forzado debe ejecutar update_client y reintentar save_order con éxito.
    """
    service = DefontanaService()

    customer = SimpleNamespace(
        rut="77.673.176-5",
        nombre="Cliente Reintento",
        correo="reintento@cliente.cl",
        celular="+56977889900",
    )
    selected_address = SimpleNamespace(
        direccion="Av. Nueva Providencia 1234",
        comuna="Providencia",
        ciudad="Santiago",
    )
    item = SimpleNamespace(
        codigo_producto="101",
        nombre_producto="SNACK PAPAS",
        tipo_empaque="unidad",
        cantidad_caja=None,
        precio_unitario=Decimal("1200"),
        cantidad=5,
        producto=SimpleNamespace(afecto=True, cantidad_caja=None),
    )
    fake_order = SimpleNamespace(
        id=uuid4(),
        cliente=customer,
        direccion=selected_address,
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

    client_in_defontana = {
        "fileID": "77.673.176-5",
        "legalCode": "77.673.176-5",
        "name": "Cliente Reintento",
        "address": "Av. Nueva Providencia 1234",
        "district": "Providencia",
        "city": "Santiago",
        "sellerID": "V01",
        "localID": "CasaMatriz",
        "paymentID": "Contado",
    }

    call_count = 0
    def mock_save_with_address_error(payload):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # Primer intento falla por dirección no encontrada
            return {"success": False, "message": "La dirección de despacho no se encuentra registrada en la ficha del cliente."}
        # Segundo intento tiene éxito
        return {"success": True, "folio": 7777}

    update_client_called = []
    def mock_update_client(cliente, direccion, client_data=None):
        update_client_called.append(direccion.direccion)
        return {"success": True}

    with patch("app.core.database.SessionLocal", return_value=FakeSession()), \
         patch.object(service, "resolve_client", return_value=client_in_defontana), \
         patch.object(service, "update_client", side_effect=mock_update_client), \
         patch.object(service, "resolve_product", return_value={"type": "A", "unit": "UN"}), \
         patch.object(service, "save_order", side_effect=mock_save_with_address_error):

        folio, err = service.sync_order(fake_order.id)
        assert folio == 7777, f"Se esperaba folio 7777 pero fue {folio}"
        assert err is None
        assert fake_order.folio_defontana_afecto == 7777
        assert fake_order.defontana_sincronizado is True
        assert call_count == 2, "Se debió reintentar save_order tras el error de dirección"
        assert len(update_client_called) >= 1

    print("test_defontana_sync_order_reactive_retry_on_address_error: OK")


def test_defontana_update_order_syncs_new_quantity_and_total():
    """
    Verifica que al editar un pedido existente (ej. Pedido #5856 de 1 a 2 unidades, $5.313 a $10.626),
    sync_order con is_update=True:
    1. Dirige la llamada a update_order (UpdateOrder) y NO a save_order.
    2. Envía 'number': 5856 sin documentTypeId.
    3. Envía el detalle actualizado con count=2, price=5313.0 y el IVA recalculado ($2.019).
    4. Sincroniza exitosamente el pedido en Defontana.
    """
    service = DefontanaService()

    customer = SimpleNamespace(rut="1-9", nombre="Cliente Pruebas")
    # Nuevo detalle con cantidad: 2 y precio 5313 (total $10.626)
    item_editado = SimpleNamespace(
        codigo_producto="PROD-5856",
        nombre_producto="Producto Modificado",
        tipo_empaque="unidad",
        cantidad_caja=None,
        precio_unitario=Decimal("5313"),
        cantidad=2,
        subtotal=Decimal("10626"),
        producto=SimpleNamespace(afecto=True, cantidad_caja=None),
    )
    fake_order = SimpleNamespace(
        id=uuid4(),
        cliente=customer,
        direccion=SimpleNamespace(direccion="Calle Comercio 123", comuna="Santiago", ciudad="Santiago"),
        detalles=[item_editado],
        folio_defontana=None,
        folio_defontana_afecto=5856,
        defontana_sincronizado=True,
        defontana_error=None,
    )

    captured_payload = {}

    def mock_update(payload):
        nonlocal captured_payload
        captured_payload = payload
        return {"success": True, "number": 5856}

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

        def scalar(self, stmt):
            return fake_order

        def commit(self):
            pass

    client_data = {
        "fileID": "1-9",
        "legalCode": "1-9",
        "name": "Cliente Pruebas",
        "address": "Calle Comercio 123",
        "district": "Santiago",
        "city": "Santiago",
        "sellerID": "V01",
        "localID": "Local",
        "paymentID": "Contado",
    }

    with patch("app.core.database.SessionLocal", return_value=FakeSession()), \
         patch.object(service, "resolve_client", return_value=client_data), \
         patch.object(service, "update_client", return_value={"success": True}), \
         patch.object(service, "resolve_product", return_value={"type": "A", "unit": "UN"}), \
         patch.object(service, "update_order", side_effect=mock_update) as mock_update_fn, \
         patch.object(service, "save_order") as mock_save_fn:

        folio, err = service.sync_order(fake_order.id, is_update=True)
        assert folio == 5856
        assert err is None
        assert fake_order.folio_defontana_afecto == 5856
        assert fake_order.defontana_sincronizado is True

        # Verificar que se llamó UpdateOrder y NO SaveOrder
        mock_update_fn.assert_called_once()
        mock_save_fn.assert_not_called()

        # Validar payload de UpdateOrder
        assert captured_payload.get("number") == 5856
        assert "documentTypeId" not in captured_payload
        assert len(captured_payload["orderDetails"]) == 1

        linea = captured_payload["orderDetails"][0]
        assert linea["count"] == 2
        assert linea["price"] == 5313.0
        assert linea["code"] == "PROD-5856"

        # Verificar IVA recalculado para $10.626: 10626 * 0.19 = 2018.94 -> 2019.0
        taxes = captured_payload.get("taxes", [])
        assert len(taxes) == 1
        assert taxes[0]["code"] == "IVA"
        assert taxes[0]["value"] == 2019.0

    print("test_defontana_update_order_syncs_new_quantity_and_total: OK")


def test_defontana_update_order_rejection_handled_properly():
    """
    Verifica que si Defontana rechaza la actualización de una orden existente,
    sync_order retorna el error y no marca sincronizado.
    """
    service = DefontanaService()
    customer = SimpleNamespace(rut="1-9", nombre="Cliente Pruebas")
    item = SimpleNamespace(
        codigo_producto="PROD-5856",
        nombre_producto="Producto",
        tipo_empaque="unidad",
        cantidad_caja=None,
        precio_unitario=Decimal("5313"),
        cantidad=2,
        producto=SimpleNamespace(afecto=True, cantidad_caja=None),
    )
    fake_order = SimpleNamespace(
        id=uuid4(),
        cliente=customer,
        direccion=SimpleNamespace(direccion="Calle 1", comuna="Santiago", ciudad="Santiago"),
        detalles=[item],
        folio_defontana=None,
        folio_defontana_afecto=5856,
        defontana_sincronizado=True,
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

    client_data = {
        "fileID": "1-9",
        "legalCode": "1-9",
        "name": "Cliente Pruebas",
        "address": "Calle 1",
        "district": "Santiago",
        "city": "Santiago",
        "sellerID": "V01",
        "localID": "Local",
        "paymentID": "Contado",
    }

    with patch("app.core.database.SessionLocal", return_value=FakeSession()), \
         patch.object(service, "resolve_client", return_value=client_data), \
         patch.object(service, "resolve_product", return_value={"type": "A", "unit": "UN"}), \
         patch.object(service, "update_order", return_value={"success": False, "message": "Orden bloqueada para edicion"}):

        folio, err = service.sync_order(fake_order.id, is_update=True)
        assert err is not None
        assert "Orden bloqueada para edicion" in err
        assert fake_order.defontana_sincronizado is False

    print("test_defontana_update_order_rejection_handled_properly: OK")


if __name__ == "__main__":
    test_defontana_save_order_mocked()
    test_defontana_item_packaging_rules()
    test_defontana_resolve_client_and_product()
    test_defontana_order_exclusively_afecto()
    test_defontana_order_exclusively_exento()
    test_defontana_order_mixed_afecto_and_exento()
    test_defontana_create_client_mocked()
    test_defontana_sync_order_creates_client_when_not_exists()
    test_defontana_sync_product_existing()
    test_defontana_sync_product_new()
    test_defontana_update_client_mocked()
    test_defontana_sync_order_propagates_selected_address_to_payload_and_client()
    test_defontana_sync_order_updates_when_address_differs_from_defontana()
    test_defontana_sync_order_reactive_retry_on_address_error()
    test_defontana_update_order_syncs_new_quantity_and_total()
    test_defontana_update_order_rejection_handled_properly()
    print("TODOS LOS TESTS DE DEFONTANA PASARON EXITOSAMENTE!")

