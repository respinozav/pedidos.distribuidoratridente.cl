import io
from decimal import Decimal
from uuid import uuid4
from fastapi import HTTPException
from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.entities import CotizacionCliente, Rol, Usuario
from app.api.dependencies import require_not_vendedor
from app.services.cotizador_service import (
    CotizacionInput,
    CotizacionItemInput,
    generar_cotizacion_pdf,
    guardar_cotizacion_en_bd,
    obtener_clientes_cotizantes,
    obtener_historial_cotizante,
    validar_email,
    validar_telefono_cl,
)


def test_cotizador_validations():
    # Email validation tests
    assert validar_email("cliente@empresa.cl") is True
    assert validar_email("juan.perez+ventas@dominio.com") is True
    assert validar_email("invalido@") is False
    assert validar_email("@dominio.cl") is False
    assert validar_email("sin_arroba.cl") is False
    assert validar_email("") is False

    # Phone validation tests (Chilean mobile)
    assert validar_telefono_cl("+56912345678") is True
    assert validar_telefono_cl("912345678") is True
    assert validar_telefono_cl("56912345678") is True
    assert validar_telefono_cl("+56 9 1234 5678") is True
    assert validar_telefono_cl("123456") is False
    assert validar_telefono_cl("+56222334455") is False  # Fijo, not mobile
    assert validar_telefono_cl("") is False


def test_cotizador_pdf_generation():
    cotizacion = CotizacionInput(
        codigo="COT-TEST01",
        cliente_nombre="Empresa de Prueba SpA",
        cliente_rut="77.888.999-0",
        cliente_correo="contacto@pruebaspa.cl",
        cliente_telefono="+56912345678",
        cliente_direccion="Av. Libertador 1234",
        cliente_comuna="Santiago",
        validez_dias=15,
        observaciones="Precios válidos por 15 días o hasta agotar stock.",
        items=[
            CotizacionItemInput(
                producto_id=str(uuid4()),
                codigo_producto="PROD-001",
                nombre_producto="Bebida Energética 500ml",
                precio_unitario=Decimal("1500"),
                cantidad=10,
                subtotal=Decimal("15000"),
                afecto=True,
                tipo_empaque="unidad",
            ),
            CotizacionItemInput(
                producto_id=str(uuid4()),
                codigo_producto="PROD-002",
                nombre_producto="Caja de Galletas Surtidas",
                precio_unitario=Decimal("12000"),
                cantidad=2,
                subtotal=Decimal("24000"),
                afecto=False,
                tipo_empaque="caja",
                cantidad_caja=24,
            ),
        ],
    )

    pdf_bytes, filename = generar_cotizacion_pdf(cotizacion)
    assert filename.startswith("Cotizacion - ")
    assert "COT-TEST01" in filename
    assert filename.endswith(".pdf")
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 1000
    # Check PDF magic header
    assert pdf_bytes[:4] == b"%PDF"


def test_cotizador_role_permissions():
    db = SessionLocal()
    colab_user = None
    admin_user = None
    vendedor_user = None
    try:
        colab_role = db.scalar(select(Rol).where(Rol.nombre == "COLABORADOR"))
        admin_role = db.scalar(select(Rol).where(Rol.nombre == "ADMINISTRADOR"))
        vendedor_role = db.scalar(select(Rol).where(Rol.nombre == "VENDEDOR"))

        assert colab_role is not None
        assert admin_role is not None
        assert vendedor_role is not None

        # 1. Colaborador
        colab_user = Usuario(
            nombre="Colab Cotizador Tester",
            correo=f"colab_cotiz_{uuid4().hex[:8]}@tridente.cl",
            password_hash=hash_password("Pass123!"),
            rol_id=colab_role.id,
            activo=True,
        )
        # 2. Administrador
        admin_user = Usuario(
            nombre="Admin Cotizador Tester",
            correo=f"admin_cotiz_{uuid4().hex[:8]}@tridente.cl",
            password_hash=hash_password("Pass123!"),
            rol_id=admin_role.id,
            activo=True,
        )
        # 3. Vendedor
        vendedor_user = Usuario(
            nombre="Vendedor Cotizador Tester",
            correo=f"vend_cotiz_{uuid4().hex[:8]}@tridente.cl",
            password_hash=hash_password("Pass123!"),
            rol_id=vendedor_role.id,
            activo=True,
        )

        db.add_all([colab_user, admin_user, vendedor_user])
        db.commit()
        db.refresh(colab_user, attribute_names=["rol"])
        db.refresh(admin_user, attribute_names=["rol"])
        db.refresh(vendedor_user, attribute_names=["rol"])

        # Test require_not_vendedor
        # Admin should pass
        res_admin = require_not_vendedor(admin_user)
        assert res_admin.id == admin_user.id

        # Colaborador should pass
        res_colab = require_not_vendedor(colab_user)
        assert res_colab.id == colab_user.id

        # Vendedor should be forbidden (403)
        try:
            require_not_vendedor(vendedor_user)
            assert False, "require_not_vendedor must raise 403 for VENDEDOR"
        except HTTPException as exc:
            assert exc.status_code == 403
    finally:
        for u in [colab_user, admin_user, vendedor_user]:
            if u and u.id:
                try:
                    db.delete(u)
                except Exception:
                    pass
        try:
            db.commit()
        except Exception:
            db.rollback()
        db.close()


def test_cotizador_historial_cotizantes():
    db = SessionLocal()
    test_folio = f"COT-TEST-{uuid4().hex[:6].upper()}"
    test_rut = "12.345.678-9"
    test_nombre = "Cliente Cotizante Unit Test SpA"
    try:
        cot = CotizacionInput(
            codigo=test_folio,
            cliente_nombre=test_nombre,
            cliente_rut=test_rut,
            cliente_correo="cotizante@test.cl",
            cliente_telefono="+56999887766",
            cliente_direccion="Calle Test 456",
            cliente_comuna="La Serena",
            validez_dias=7,
            items=[
                CotizacionItemInput(
                    producto_id=str(uuid4()),
                    codigo_producto="TEST-SKU-99",
                    nombre_producto="Producto Test Historial",
                    precio_unitario=Decimal("5000"),
                    cantidad=3,
                    subtotal=Decimal("15000"),
                    afecto=True,
                    tipo_empaque="caja",
                    cantidad_caja=12,
                )
            ],
        )

        # 1. Guardar cotización
        guardada = guardar_cotizacion_en_bd(db, cot)
        assert guardada.folio == test_folio
        assert guardada.cliente_rut == test_rut
        assert guardada.total == Decimal("17850")  # 15000 + 19% iva = 17850

        # 2. Listar clientes cotizantes
        cotizantes = obtener_clientes_cotizantes(db, query="12345678")
        assert len(cotizantes) >= 1
        found = next((c for c in cotizantes if c["nombre"] == test_nombre), None)
        assert found is not None
        assert found["rut"] == test_rut
        assert found["correo"] == "cotizante@test.cl"

        # 3. Obtener historial detallado de cotizaciones y productos
        historial = obtener_historial_cotizante(db, test_rut)
        assert len(historial) >= 1
        hist_item = next((h for h in historial if h["folio"] == test_folio), None)
        assert hist_item is not None
        assert hist_item["cliente_razon_social"] == test_nombre
        assert len(hist_item["items"]) == 1
        assert hist_item["items"][0]["codigo_sku"] == "TEST-SKU-99"
        assert hist_item["items"][0]["nombre_producto"] == "Producto Test Historial"
        assert hist_item["items"][0]["cantidad"] == 3
        assert hist_item["items"][0]["precio_unitario"] == 5000.0

    finally:
        try:
            cot_db = db.query(CotizacionCliente).filter(CotizacionCliente.folio == test_folio).first()
            if cot_db:
                db.delete(cot_db)
                db.commit()
        except Exception:
            db.rollback()
        db.close()


if __name__ == "__main__":
    print("Ejecutando test_cotizador_validations...")
    test_cotizador_validations()
    print("Ejecutando test_cotizador_pdf_generation...")
    test_cotizador_pdf_generation()
    print("Ejecutando test_cotizador_role_permissions...")
    test_cotizador_role_permissions()
    print("Ejecutando test_cotizador_historial_cotizantes...")
    test_cotizador_historial_cotizantes()
    print("[OK] Todos los tests de Cotizador completados con exito!")

