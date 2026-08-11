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
            )
        ],
        total=Decimal("2000"),
    )

    pdf = _order_pdf(order)

    assert pdf.startswith(b"%PDF-1.4")
    assert len(pdf) > 500
