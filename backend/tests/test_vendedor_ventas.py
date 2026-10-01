import uuid
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.database import Base, get_db
from app.core.security import create_access_token, hash_password
from app.main import app
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


def run_tests():
    # Setup database session
    db_gen = get_db()
    db = next(db_gen)

    try:
        # 1. Ensure VENDEDOR role exists
        vendedor_role = db.scalar(select(Rol).where(Rol.nombre == "VENDEDOR"))
        if not vendedor_role:
            vendedor_role = Rol(nombre="VENDEDOR", activo=True)
            db.add(vendedor_role)
            db.flush()

        # 2. Create test vendedor user
        test_vendedor = Usuario(
            nombre="Juan Vendedor Test",
            correo=f"vendedor_{uuid.uuid4().hex[:6]}@tridente.cl",
            password_hash=hash_password("password123"),
            rol_id=vendedor_role.id,
            activo=True,
        )
        db.add(test_vendedor)
        db.flush()

        # 3. Create test category with 15% commission
        test_cat = Categoria(
            nombre=f"CAT_TEST_{uuid.uuid4().hex[:6]}",
            comision_porcentaje=Decimal("15.00"),
            activo=True,
        )
        db.add(test_cat)
        db.flush()

        # 4. Create test product
        test_prod = Producto(
            categoria_id=test_cat.id,
            codigo=f"COD_{uuid.uuid4().hex[:6]}",
            nombre="Producto Test Comisión",
            precio=Decimal("2000.00"),
            cantidad=100,
            activo=True,
        )
        db.add(test_prod)
        db.flush()

        # 5. Create test customer and address
        test_cli = Cliente(
            nombre="Empresa Compradora SpA",
            rut="76123456-7",
            correo=f"cliente_{uuid.uuid4().hex[:6]}@cliente.cl",
            password_hash=hash_password("password123"),
            activo=True,
            porcentaje=Decimal("0.00"),
        )
        db.add(test_cli)
        db.flush()

        test_dir = Direccion(
            cliente_id=test_cli.id,
            direccion="Av. Principal 123",
            comuna="Santiago",
            principal=True,
            activo=True,
        )
        db.add(test_dir)

        # 6. Ensure active order state
        estado = db.scalar(select(Estado).where(Estado.activo.is_(True)))
        if not estado:
            estado = Estado(nombre="Pedido", activo=True)
            db.add(estado)

        db.commit()

        # Tokens
        vendedor_token = create_access_token(test_vendedor.id, "VENDEDOR")

        client = TestClient(app)

        # Test A: List clients as vendor
        res_clients = client.get(
            "/api/admin/vendedor/clientes",
            headers={"Authorization": f"Bearer {vendedor_token}"},
        )
        assert res_clients.status_code == 200, res_clients.text
        client_list = res_clients.json()
        assert any(c["id"] == str(test_cli.id) for c in client_list)

        # Test B: Iniciar venta
        res_iniciar = client.post(
            "/api/admin/vendedor/iniciar-venta",
            json={"cliente_id": str(test_cli.id)},
            headers={"Authorization": f"Bearer {vendedor_token}"},
        )
        assert res_iniciar.status_code == 200, res_iniciar.text
        iniciar_data = res_iniciar.json()
        customer_impersonated_token = iniciar_data["access_token"]
        assert iniciar_data["cliente_id"] == str(test_cli.id)
        assert iniciar_data["vendedor_id"] == str(test_vendedor.id)

        # Test C: Create order using impersonated customer token
        order_payload = {
            "direccion_id": str(test_dir.id),
            "productos": [
                {
                    "producto_id": str(test_prod.id),
                    "cantidad": 3,
                    "tipo_empaque": "unidad",
                }
            ],
        }
        res_order = client.post(
            f"/api/clientes/{test_cli.id}/pedidos",
            json=order_payload,
            headers={"Authorization": f"Bearer {customer_impersonated_token}"},
        )
        assert res_order.status_code == 201, res_order.text
        order_data = res_order.json()
        assert order_data["vendedor_id"] == str(test_vendedor.id)
        assert Decimal(str(order_data["total"])) == Decimal("6000.00")

        # Verify DB records
        order_id = uuid.UUID(order_data["id"])
        venta_vendedor = db.scalar(
            select(VentaVendedor).where(VentaVendedor.pedido_id == order_id)
        )
        assert venta_vendedor is not None
        assert venta_vendedor.vendedor_id == test_vendedor.id
        assert venta_vendedor.cliente_id == test_cli.id
        assert venta_vendedor.total_venta == Decimal("6000.00")
        # 15% of 6000 is 900.00
        assert venta_vendedor.comision_total == Decimal("900.00")
        assert len(venta_vendedor.detalles) == 1
        assert venta_vendedor.detalles[0].comision_porcentaje == Decimal("15.00")
        assert venta_vendedor.detalles[0].comision_monto == Decimal("900.00")

        # Test D: Query /api/admin/vendedor/ventas
        res_ventas = client.get(
            "/api/admin/vendedor/ventas",
            headers={"Authorization": f"Bearer {vendedor_token}"},
        )
        assert res_ventas.status_code == 200, res_ventas.text
        ventas_data = res_ventas.json()
        assert Decimal(str(ventas_data["total_ventas"])) >= Decimal("6000.00")
        assert Decimal(str(ventas_data["total_comisiones"])) >= Decimal("900.00")
        assert ventas_data["cantidad_pedidos"] >= 1
        found_item = next(item for item in ventas_data["items"] if item["id"] == str(venta_vendedor.id))
        assert found_item["cliente"]["id"] == str(test_cli.id)
        assert len(found_item["detalles"]) == 1
        assert Decimal(str(found_item["detalles"][0]["comision_monto"])) == Decimal("900.00")

        # Test E: Standard customer order (not through vendor) -> should NOT record VentaVendedor
        customer_regular_token = create_access_token(test_cli.id, "CLIENTE")
        res_reg_order = client.post(
            f"/api/clientes/{test_cli.id}/pedidos",
            json=order_payload,
            headers={"Authorization": f"Bearer {customer_regular_token}"},
        )
        assert res_reg_order.status_code == 201, res_reg_order.text
        reg_order_data = res_reg_order.json()
        assert reg_order_data.get("vendedor_id") is None
        reg_order_id = uuid.UUID(reg_order_data["id"])
        reg_venta = db.scalar(
            select(VentaVendedor).where(VentaVendedor.pedido_id == reg_order_id)
        )
        assert reg_venta is None

        print("All test_vendedor_ventas tests PASSED successfully!")
    finally:
        db.close()


if __name__ == "__main__":
    run_tests()
