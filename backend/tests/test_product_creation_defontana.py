from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

from fastapi import HTTPException

from app.controllers.routes import create_product
from app.models.entities import Categoria, Usuario
from app.schemas.dto import ProductInput
from app.services.defontana_service import DefontanaService


def test_create_product_endpoint_replicates_to_defontana():
    fake_category_id = uuid4()
    fake_cat = Categoria(id=fake_category_id, nombre="BEBIDAS", activo=True)
    fake_admin = Usuario(id=uuid4(), nombre="Admin", activo=True)

    mock_db = MagicMock()
    mock_db.scalar.side_effect = [
        None,      # Comprobación de duplicados (no existe localmente)
        fake_cat,  # Comprobación de categoría existente
    ]

    payload = ProductInput(
        codigo="PROD-TEST-001",
        nombre="BEBIDA COLA 500ML",
        categoria_id=fake_category_id,
        precio=Decimal("1500"),
        cantidad=24,
        activo=True,
        afecto=True,
    )

    with patch("app.controllers.routes.DefontanaService") as MockDefontanaService, \
         patch("app.controllers.routes.Repository") as MockRepo, \
         patch("app.controllers.routes.invalidate_catalog_cache"), \
         patch("app.controllers.routes.procesar_avisos_stock_disponible"):

        mock_instance = MockDefontanaService.return_value
        mock_instance.is_configured.return_value = True
        mock_instance.sync_product.return_value = (True, None)
        MockRepo.return_value.add.side_effect = lambda entity: entity

        created = create_product(payload=payload, database=mock_db, _=fake_admin)

        # 1. Verifica que se invocó a Defontana con los datos exactos del producto
        mock_instance.sync_product.assert_called_once_with(
            code="PROD-TEST-001",
            name="BEBIDA COLA 500ML",
            price=Decimal("1500"),
            category_name="BEBIDAS",
        )
        # 2. Verifica que se persistió en la BD local tras la respuesta exitosa
        mock_db.commit.assert_called_once()
        assert created.codigo == "PROD-TEST-001"
        assert created.precio == Decimal("1500")

    print("  [OK] test_create_product_endpoint_replicates_to_defontana")


def test_create_product_endpoint_blocks_save_when_defontana_rejects():
    fake_category_id = uuid4()
    fake_cat = Categoria(id=fake_category_id, nombre="BEBIDAS", activo=True)
    fake_admin = Usuario(id=uuid4(), nombre="Admin", activo=True)

    mock_db = MagicMock()
    mock_db.scalar.side_effect = [
        None,      # No duplicado local
        fake_cat,  # Categoría encontrada
    ]

    payload = ProductInput(
        codigo="PROD-TEST-002",
        nombre="BEBIDA NARANJA 500ML",
        categoria_id=fake_category_id,
        precio=Decimal("1600"),
        cantidad=12,
        activo=True,
        afecto=True,
    )

    with patch("app.controllers.routes.DefontanaService") as MockDefontanaService, \
         patch("app.controllers.routes.Repository") as MockRepo:

        mock_instance = MockDefontanaService.return_value
        mock_instance.is_configured.return_value = True
        mock_instance.sync_product.return_value = (False, "Código ya existe en Defontana con otra unidad")

        # Debe lanzar HTTPException 400 y NO guardar nada en la BD
        failed = False
        try:
            create_product(payload=payload, database=mock_db, _=fake_admin)
        except HTTPException as exc:
            failed = True
            assert exc.status_code == 400
            assert "Código ya existe en Defontana con otra unidad" in exc.detail
            mock_db.commit.assert_not_called()

        assert failed, "Debió haber lanzado HTTPException por rechazo de Defontana"

    print("  [OK] test_create_product_endpoint_blocks_save_when_defontana_rejects")


def test_defontana_service_save_product_payload_structure():
    service = DefontanaService()
    captured_payload = {}

    def mock_save_product(payload):
        nonlocal captured_payload
        captured_payload = payload
        return {"success": True, "message": "Producto creado"}

    with patch.object(service, "is_configured", return_value=True), \
         patch.object(service, "resolve_product", return_value=None), \
         patch.object(service, "get_categories", return_value=[{"categoryID": 42, "description": "LIMPIEZA"}]), \
         patch.object(service, "save_product", side_effect=mock_save_product):

        ok, err = service.sync_product(
            code="LIMP-500",
            name="DETERGENTE LIQUIDO 3L",
            price=Decimal("4990"),
            category_name="LIMPIEZA",
        )

        assert ok is True
        assert err is None
        assert captured_payload["code"] == "LIMP-500"
        assert captured_payload["name"] == "DETERGENTE LIQUIDO 3L"
        assert captured_payload["price"] == 4990.0
        assert captured_payload["unit"] == "UN"
        assert captured_payload["categoryID"] == 42
        assert captured_payload["isService"] is False
        assert captured_payload["usaLotes"] is False

    print("  [OK] test_defontana_service_save_product_payload_structure")


if __name__ == "__main__":
    print("\nIniciando pruebas de replicación de productos en Defontana:")
    test_create_product_endpoint_replicates_to_defontana()
    test_create_product_endpoint_blocks_save_when_defontana_rejects()
    test_defontana_service_save_product_payload_structure()
    print("\n¡TODAS LAS PRUEBAS DE CREACION Y REPLICACION A DEFONTANA PASARON CON EXITO!\n")
