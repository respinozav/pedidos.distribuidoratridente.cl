import io
from decimal import Decimal
from uuid import uuid4
from fastapi import HTTPException
from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.entities import Rol, Usuario
from app.api.dependencies import require_not_vendedor
from app.services.cotizador_service import (
    CotizacionInput,
    CotizacionItemInput,
    generar_cotizacion_pdf,
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
