from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace

from app.services.notifications import _order_pdf, _product_detail_label


def test_product_detail_label_compacts_code_on_same_line() -> None:
    detail = SimpleNamespace(nombre_producto="Producto de prueba", codigo_producto="PR-001")

    label = _product_detail_label(detail)

    assert "Producto de prueba" in label
    assert "PR-001" in label
    assert "<br" not in label


def test_order_pdf_contains_valid_header() -> None:
    order = SimpleNamespace(
        id="12345678-1234-1234-1234-123456789abc",
        cliente=SimpleNamespace(nombre="Cliente de Prueba", rut="1-9", correo="cliente@example.com", celular="+56912345678"),
        direccion=SimpleNamespace(direccion="Calle Principal 123", comuna="Santiago"),
        created_at=datetime.now(UTC),
        detalles=[
            SimpleNamespace(
                codigo_producto="PR-001",
                cantidad=2,
                nombre_producto="Producto de prueba",
                precio_unitario=Decimal("1000"),
                subtotal=Decimal("2000"),
                afecto=True,
                producto=SimpleNamespace(afecto=True),
            )
        ],
        total=Decimal("2000"),
    )

    pdf = _order_pdf(order)

    assert pdf.startswith(b"%PDF-1.4")
    assert len(pdf) > 500


def test_order_pdf_with_mixed_afecto_and_exento() -> None:
    order = SimpleNamespace(
        id="87654321-4321-4321-4321-abcdef123456",
        cliente=SimpleNamespace(nombre="Juan Perez", rut="12.345.678-9", correo="juan@example.com", celular="+56999999999"),
        direccion=SimpleNamespace(direccion="Av. Los Aromos 456", comuna="La Serena"),
        created_at=datetime.now(UTC),
        detalles=[
            SimpleNamespace(
                codigo_producto="EX-001",
                cantidad=1,
                nombre_producto="Producto Exento Primero",
                precio_unitario=Decimal("3000"),
                subtotal=Decimal("3000"),
                producto=SimpleNamespace(afecto=False),
            ),
            SimpleNamespace(
                codigo_producto="AF-001",
                cantidad=3,
                nombre_producto="Producto Afecto Segundo",
                precio_unitario=Decimal("1500"),
                subtotal=Decimal("4500"),
                producto=SimpleNamespace(afecto=True),
            ),
        ],
        total=Decimal("7500"),
    )

    pdf = _order_pdf(order)
    assert pdf.startswith(b"%PDF-1.4")
    assert len(pdf) > 500


def test_notify_administrators_only_sends_to_recibe_pedido_users(monkeypatch) -> None:
    from app.services.notifications import notify_administrators_of_order

    sent_messages = []

    class FakeSMTP:
        def __init__(self, host, port, timeout=20):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

        def login(self, user, password):
            pass

        def send_message(self, message):
            sent_messages.append(message)

    monkeypatch.setattr("smtplib.SMTP_SSL", FakeSMTP)
    class FakeWhatsAppService:
        instance_name = "test_instance"
        def is_connected_sync(self):
            return False

    monkeypatch.setattr("app.services.notifications.WhatsAppService", FakeWhatsAppService)
    monkeypatch.setattr("app.services.whatsapp_service.WhatsAppService", FakeWhatsAppService)
    monkeypatch.setattr(
        "app.services.notifications.get_settings",
        lambda: SimpleNamespace(
            smtp_configured=True,
            smtp_host="localhost",
            smtp_port=465,
            smtp_username="test@example.com",
            smtp_password="pwd",
            smtp_from_name="Distribuidora Tridente",
            smtp_from_email="pedidos@tridente.cl",
        ),
    )


    class FakeDatabase:
        def __init__(self, recipients):
            self._recipients = recipients
            self.added = []

        def scalars(self, statement):
            return self._recipients

        def add(self, instance):
            self.added.append(instance)

        def commit(self):
            pass

        def rollback(self):
            pass

    order = SimpleNamespace(
        id="12345678-1234-1234-1234-123456789abc",
        cliente=SimpleNamespace(nombre="Cliente", rut="1-9", correo="cliente@example.com", celular="+56912345678"),
        direccion=SimpleNamespace(direccion="Calle 1", comuna="Santiago"),
        created_at=datetime.now(UTC),
        detalles=[],
        total=Decimal("1000"),
    )

    # Caso 1: Hay usuarios con recibe_pedido = True
    db = FakeDatabase(["admin_pedidos@example.com"])
    notify_administrators_of_order(db, order)

    assert len(sent_messages) == 2
    recipients = [msg["To"] for msg in sent_messages]
    assert "admin_pedidos@example.com" in recipients
    assert "cliente@example.com" in recipients
    assert len(db.added) > 0  # Se registraron logs

    # Caso 2: No hay usuarios con recibe_pedido = True (recibe_pedido = False para todos)
    sent_messages.clear()
    db_empty = FakeDatabase([])
    notify_administrators_of_order(db_empty, order)

    assert len(sent_messages) == 1
    assert sent_messages[0]["To"] == "cliente@example.com"


