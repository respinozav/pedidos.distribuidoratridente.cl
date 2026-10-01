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
    db_gen = get_db()
    db = next(db_gen)

    try:
        # 1. Ensure roles exist
        admin_role = db.scalar(select(Rol).where(Rol.nombre == "ADMINISTRADOR"))
        if not admin_role:
            admin_role = Rol(nombre="ADMINISTRADOR", activo=True)
            db.add(admin_role)
            db.flush()

        vendedor_role = db.scalar(select(Rol).where(Rol.nombre == "VENDEDOR"))
        if not vendedor_role:
            vendedor_role = Rol(nombre="VENDEDOR", activo=True)
            db.add(vendedor_role)
            db.flush()

        # 2. Create admin & vendedor users
        admin_user = Usuario(
            nombre="Admin Test",
            correo=f"admin_{uuid.uuid4().hex[:6]}@tridente.cl",
            password_hash=hash_password("admin123"),
            rol_id=admin_role.id,
            activo=True,
        )
        db.add(admin_user)

        vendedor_user = Usuario(
            nombre="Vendedor Test",
            correo=f"vendedor_{uuid.uuid4().hex[:6]}@tridente.cl",
            password_hash=hash_password("vend123"),
            rol_id=vendedor_role.id,
            activo=True,
        )
        db.add(vendedor_user)
        db.commit()
        db.refresh(admin_user)
        db.refresh(vendedor_user)

        # 3. Create tokens
        admin_token = create_access_token(admin_user.id, "ADMINISTRADOR")
        vendedor_token = create_access_token(vendedor_user.id, "VENDEDOR")

        client = TestClient(app)

        # 4. Test vendedor is forbidden
        res_vendedor = client.get("/api/admin/ventas", headers={"Authorization": f"Bearer {vendedor_token}"})
        assert res_vendedor.status_code == 403, f"Expected 403 for VENDEDOR, got {res_vendedor.status_code}"

        # 5. Test admin can access
        res_admin = client.get("/api/admin/ventas", headers={"Authorization": f"Bearer {admin_token}"})
        assert res_admin.status_code == 200, f"Expected 200 for ADMIN, got {res_admin.status_code}: {res_admin.text}"
        data = res_admin.json()
        assert "total_ventas" in data
        assert "total_comisiones" in data
        assert "vendedores_resumen" in data
        assert "vendedores_disponibles" in data
        assert "items" in data

        print("test_admin_ventas PASSED successfully!")
    finally:
        try:
            db.delete(vendedor_user)
            db.delete(admin_user)
            db.commit()
        except Exception:
            db.rollback()


if __name__ == "__main__":
    run_tests()
