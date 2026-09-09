import uuid
from decimal import Decimal
from pydantic import ValidationError

from app.models.entities import Categoria, Producto
from app.schemas.dto import ProductInput, ProductOutput
from app.controllers.routes import create_product, update_product, list_stock_alert_products
from app.core.database import SessionLocal


def test_product_input_validation():
    dummy_cat = uuid.uuid4()

    # 1. notificar_stock=False -> stock_notificacion se normaliza a None
    p1 = ProductInput(
        categoria_id=dummy_cat,
        codigo="TESTNOTIF1",
        nombre="PRODUCTO TEST 1",
        precio=Decimal("1000"),
        cantidad=50,
        notificar_stock=False,
        stock_notificacion=15,  # debe normalizarse a None
    )
    assert p1.notificar_stock is False
    assert p1.stock_notificacion is None

    # 2. notificar_stock=True sin stock_notificacion -> error
    try:
        ProductInput(
            categoria_id=dummy_cat,
            codigo="TESTNOTIF2",
            nombre="PRODUCTO TEST 2",
            precio=Decimal("1000"),
            cantidad=50,
            notificar_stock=True,
            stock_notificacion=None,
        )
        assert False, "Debe fallar cuando notificar_stock=True y stock_notificacion es None"
    except (ValidationError, ValueError):
        pass

    # 3. notificar_stock=True con stock_notificacion < 1 -> error
    for invalid_stock in [0, -1, -5]:
        try:
            ProductInput(
                categoria_id=dummy_cat,
                codigo="TESTNOTIF3",
                nombre="PRODUCTO TEST 3",
                precio=Decimal("1000"),
                cantidad=50,
                notificar_stock=True,
                stock_notificacion=invalid_stock,
            )
            assert False, f"Debe fallar cuando stock_notificacion={invalid_stock} < 1"
        except (ValidationError, ValueError):
            pass

    # 4. notificar_stock=True con stock_notificacion >= 1 -> éxito
    p4 = ProductInput(
        categoria_id=dummy_cat,
        codigo="TESTNOTIF4",
        nombre="PRODUCTO TEST 4",
        precio=Decimal("1000"),
        cantidad=50,
        notificar_stock=True,
        stock_notificacion=1,
    )
    assert p4.notificar_stock is True
    assert p4.stock_notificacion == 1


def test_product_crud_stock_notification():
    db = SessionLocal()
    try:
        categoria = db.query(Categoria).filter(Categoria.activo.is_(True), Categoria.eliminado_at.is_(None)).first()
        if not categoria:
            categoria = Categoria(nombre=f"CAT_TEST_{uuid.uuid4().hex[:6]}", activo=True)
            db.add(categoria)
            db.commit()

        admin_mock = type("MockUser", (), {"id": uuid.uuid4(), "nombre": "Admin"})()

        # Crear producto con notificar_stock activo (> 10)
        code = f"TNOTIF_{uuid.uuid4().hex[:6].upper()}"
        payload = ProductInput(
            categoria_id=categoria.id,
            codigo=code,
            nombre="PRODUCTO CON ALERTA STOCK",
            precio=Decimal("5000"),
            cantidad=25,
            notificar_stock=True,
            stock_notificacion=15,
        )
        created = create_product(payload, db, admin_mock)
        assert created.id is not None
        assert created.notificar_stock is True
        assert created.stock_notificacion == 15

        # Actualizar a notificar_stock desactivado
        update_payload = ProductInput(
            categoria_id=categoria.id,
            codigo=code,
            nombre="PRODUCTO CON ALERTA STOCK",
            precio=Decimal("5000"),
            cantidad=25,
            notificar_stock=False,
            stock_notificacion=None,
        )
        updated = update_product(created.id, update_payload, db, admin_mock)
        assert updated.notificar_stock is False
        assert updated.stock_notificacion is None

        # Limpiar
        db.delete(created)
        db.commit()
    finally:
        db.close()


def test_stock_alert_query():
    db = SessionLocal()
    admin_mock = type("MockUser", (), {"id": uuid.uuid4(), "nombre": "Admin"})()
    created_products = []
    try:
        categoria = db.query(Categoria).filter(Categoria.activo.is_(True), Categoria.eliminado_at.is_(None)).first()
        if not categoria:
            categoria = Categoria(nombre=f"CAT_TEST_{uuid.uuid4().hex[:6]}", activo=True)
            db.add(categoria)
            db.commit()

        # Producto 1: notificar_stock=True, cantidad=0, stock_notificacion=10 (Debe alertar, como Bon o Bon 526)
        p1 = Producto(
            categoria_id=categoria.id,
            codigo=f"ALERTA_1_{uuid.uuid4().hex[:4].upper()}",
            nombre="PRODUCTO TEST CRITICO",
            precio=Decimal("1500"),
            cantidad=0,
            notificar_stock=True,
            stock_notificacion=10,
            activo=True,
        )
        db.add(p1)

        # Producto 2: notificar_stock=True, cantidad=50, stock_notificacion=10 (No debe alertar, cantidad > 10)
        p2 = Producto(
            categoria_id=categoria.id,
            codigo=f"ALERTA_2_{uuid.uuid4().hex[:4].upper()}",
            nombre="PRODUCTO TEST CON STOCK",
            precio=Decimal("1500"),
            cantidad=50,
            notificar_stock=True,
            stock_notificacion=10,
            activo=True,
        )
        db.add(p2)

        # Producto 3: notificar_stock=False, cantidad=0 (No debe alertar porque notificar_stock=False)
        p3 = Producto(
            categoria_id=categoria.id,
            codigo=f"ALERTA_3_{uuid.uuid4().hex[:4].upper()}",
            nombre="PRODUCTO TEST NO NOTIFICAR",
            precio=Decimal("1500"),
            cantidad=0,
            notificar_stock=False,
            stock_notificacion=None,
            activo=True,
        )
        db.add(p3)

        db.commit()
        db.refresh(p1)
        db.refresh(p2)
        db.refresh(p3)
        created_products = [p1, p2, p3]

        alerts = list_stock_alert_products(db, admin_mock)
        alert_ids = [str(a.id) for a in alerts]

        assert str(p1.id) in alert_ids, "El producto p1 (cantidad=0, notif=10) debe estar en la lista de alertas"
        assert str(p2.id) not in alert_ids, "El producto p2 (cantidad=50, notif=10) NO debe estar en la lista de alertas"
        assert str(p3.id) not in alert_ids, "El producto p3 (notificar_stock=False) NO debe estar en la lista de alertas"

    finally:
        for prod in created_products:
            try:
                db.delete(prod)
            except Exception:
                pass
        db.commit()
        db.close()


if __name__ == "__main__":
    test_product_input_validation()
    test_product_crud_stock_notification()
    test_stock_alert_query()
    print(">>> test_producto_notificar_stock PASSED! <<<")

