import uuid
from decimal import Decimal
from unittest.mock import MagicMock
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import hash_password
from app.models.entities import (
    Categoria,
    Cliente,
    Direccion,
    Estado,
    Pedido,
    Producto,
    Rol,
    Usuario,
    VentaVendedor,
    DetalleVentaVendedor,
)
from app.schemas.dto import (
    AsignacionCarteraInput,
    AsignacionCarteraMasivaInput,
    OrderCreate,
    OrderLineInput,
)
from app.services.ordering import OrderService
from app.controllers.routes import (
    list_admin_cartera,
    asignar_cliente_cartera,
    desasignar_cliente_cartera,
    asignar_masivo_cartera,
)


def run_cartera_tests():
    db_gen = get_db()
    db = next(db_gen)

    try:
        # 1. Ensure VENDEDOR and ADMIN roles
        vendedor_role = db.scalar(select(Rol).where(Rol.nombre == "VENDEDOR"))
        if not vendedor_role:
            vendedor_role = Rol(nombre="VENDEDOR", activo=True)
            db.add(vendedor_role)
            db.flush()

        admin_role = db.scalar(select(Rol).where(Rol.nombre == "ADMINISTRADOR"))
        if not admin_role:
            admin_role = Rol(nombre="ADMINISTRADOR", activo=True)
            db.add(admin_role)
            db.flush()

        # 2. Create test vendedor
        test_vendedor = Usuario(
            nombre="Vendedor Cartera Test",
            correo=f"vendedor_{uuid.uuid4().hex[:6]}@cartera.cl",
            password_hash=hash_password("password123"),
            rol_id=vendedor_role.id,
            activo=True,
        )
        db.add(test_vendedor)
        db.flush()

        # 3. Create test admin mock
        test_admin = Usuario(
            nombre="Admin Test",
            correo=f"admin_{uuid.uuid4().hex[:6]}@cartera.cl",
            password_hash=hash_password("password123"),
            rol_id=admin_role.id,
            activo=True,
        )
        db.add(test_admin)
        db.flush()

        # 4. Create test category with 10% commission
        test_cat = Categoria(
            nombre=f"CAT_CARTERA_{uuid.uuid4().hex[:6]}",
            comision_porcentaje=Decimal("10.00"),
            activo=True,
        )
        db.add(test_cat)
        db.flush()

        # 5. Create test product
        test_prod = Producto(
            categoria_id=test_cat.id,
            codigo=f"PROD_{uuid.uuid4().hex[:6]}",
            nombre="Producto Cartera Comision",
            precio=Decimal("5000.00"),
            cantidad=50,
            activo=True,
        )
        db.add(test_prod)
        db.flush()

        # 6. Create test customer
        test_cli = Cliente(
            nombre="Almacen Cartera Test",
            rut="77888999-1",
            correo=f"cliente_{uuid.uuid4().hex[:6]}@cartera.cl",
            password_hash=hash_password("password123"),
            activo=True,
            vendedor_id=None,
        )
        db.add(test_cli)
        db.flush()

        test_dir = Direccion(
            cliente_id=test_cli.id,
            direccion="Calle Comercio 456",
            comuna="Providencia",
            principal=True,
            activo=True,
        )
        db.add(test_dir)

        # 7. Active order state
        estado = db.scalar(select(Estado).where(Estado.activo.is_(True)))
        if not estado:
            estado = Estado(nombre="Pedido", activo=True)
            db.add(estado)

        db.commit()

        # TEST A: Asignar cliente a vendedor
        res_asignar = asignar_cliente_cartera(
            payload=AsignacionCarteraInput(cliente_id=test_cli.id, vendedor_id=test_vendedor.id),
            database=db,
            _=test_admin,
        )
        assert res_asignar.success is True
        db.refresh(test_cli)
        assert test_cli.vendedor_id == test_vendedor.id

        # TEST B: Listar cartera
        res_cartera = list_admin_cartera(
            database=db,
            _=test_admin,
            vendedor_id=test_vendedor.id,
        )
        assert res_cartera.total_clientes >= 1
        assert any(item.id == test_cli.id and item.vendedor_id == test_vendedor.id for item in res_cartera.items)

        # TEST C: Cliente realiza pedido directamente (sin vendedor_id en el payload o session)
        order_payload = OrderCreate(
            direccion_id=test_dir.id,
            productos=[OrderLineInput(producto_id=test_prod.id, cantidad=2)],
        )
        order_service = OrderService(db)
        # customer_id=test_cli.id, vendedor_id=None (cliente hace pedido por sí mismo)
        created_order = order_service.create(customer_id=test_cli.id, payload=order_payload, vendedor_id=None)

        assert created_order.vendedor_id == test_vendedor.id
        venta_vendedor = db.scalar(select(VentaVendedor).where(VentaVendedor.pedido_id == created_order.id))
        assert venta_vendedor is not None
        assert venta_vendedor.vendedor_id == test_vendedor.id
        # Total = 5000 * 2 = 10000. Comision = 10% de 10000 = 1000.
        assert venta_vendedor.total_venta == Decimal("10000.00")
        assert venta_vendedor.comision_total == Decimal("1000.00")

        # TEST D: Desasignar cliente
        res_desasignar = desasignar_cliente_cartera(
            cliente_id=test_cli.id,
            database=db,
            _=test_admin,
        )
        assert res_desasignar.success is True
        db.refresh(test_cli)
        assert test_cli.vendedor_id is None

        print("ALL CARTERA TESTS PASSED SUCCESSFULLY!")

    finally:
        db.close()


if __name__ == "__main__":
    run_cartera_tests()
