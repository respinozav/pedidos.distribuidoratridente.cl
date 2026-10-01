from decimal import Decimal
from uuid import uuid4
from fastapi import HTTPException
from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.entities import Categoria, Rol, Usuario
from app.api.dependencies import require_admin_or_vendedor, require_not_vendedor, require_super_admin
from app.controllers.routes import admin_profile, create_category, list_credits, list_customers
from app.schemas.dto import CategoryInput


def test_vendedor_role_and_category_commission():
    db = SessionLocal()
    vendedor_user = None
    admin_user = None
    test_cat = None
    try:
        # 1. Verify VENDEDOR and ADMINISTRADOR roles exist
        vendedor_role = db.scalar(select(Rol).where(Rol.nombre == "VENDEDOR"))
        assert vendedor_role is not None, "Role VENDEDOR must exist in database"
        assert vendedor_role.activo is True

        admin_role = db.scalar(select(Rol).where(Rol.nombre == "ADMINISTRADOR"))
        assert admin_role is not None, "Role ADMINISTRADOR must exist in database"
        assert admin_role.activo is True

        # 2. Test Category comision_porcentaje column & DTO
        cat_name = f"Test Cat Comision {uuid4().hex[:6]}"
        test_cat = Categoria(
            nombre=cat_name,
            comision_porcentaje=Decimal("12.50"),
            porcentaje=Decimal("0.00"),
            usa_porcentaje_cliente=True,
            activo=True,
            en_catalogo_publico=True,
        )
        db.add(test_cat)
        db.commit()
        db.refresh(test_cat)

        assert test_cat.comision_porcentaje == Decimal("12.50"), f"Expected 12.50, got {test_cat.comision_porcentaje}"

        # 3. Create a test Vendedor user
        vendedor_email = f"vendedor_test_{uuid4().hex[:8]}@tridente.cl"
        vendedor_user = Usuario(
            nombre="Vendedor Tester",
            correo=vendedor_email,
            password_hash=hash_password("VendedorPass123!"),
            rol_id=vendedor_role.id,
            activo=True,
            celular="+56911223344",
            recibe_pedido=False,
        )
        db.add(vendedor_user)

        # Create a test Admin user
        admin_email = f"admin_test_{uuid4().hex[:8]}@tridente.cl"
        admin_user = Usuario(
            nombre="Admin Tester",
            correo=admin_email,
            password_hash=hash_password("AdminPass123!"),
            rol_id=admin_role.id,
            activo=True,
            celular="+56999887766",
            recibe_pedido=False,
        )
        db.add(admin_user)
        db.commit()
        db.refresh(vendedor_user, attribute_names=["rol"])
        db.refresh(admin_user, attribute_names=["rol"])

        # 4. Test require_super_admin with Vendedor -> must raise 403 Forbidden
        try:
            require_super_admin(vendedor_user)
            assert False, "require_super_admin should have raised HTTPException 403 for VENDEDOR"
        except HTTPException as exc:
            assert exc.status_code == 403
            assert "administradores" in exc.detail.lower()

        # 5. Test require_not_vendedor with Vendedor -> must raise 403 Forbidden
        try:
            require_not_vendedor(vendedor_user)
            assert False, "require_not_vendedor should have raised HTTPException 403 for VENDEDOR"
        except HTTPException as exc:
            assert exc.status_code == 403
            assert "vendedor" in exc.detail.lower()

        # 6. Test require_not_vendedor with Admin -> must succeed
        allowed_admin = require_not_vendedor(admin_user)
        assert allowed_admin.id == admin_user.id

        # 7. Test admin_profile works for Vendedor
        profile = admin_profile(database=db, current_admin=vendedor_user)
        assert profile is not None
        assert profile.id == vendedor_user.id
        assert profile.rol.nombre == "VENDEDOR"

        # 8. Test list_credits works with AdminUser (which accepts Vendedor)
        credits_result = list_credits(database=db, _=vendedor_user, pagado=False)
        assert isinstance(credits_result, list)

        # 9. Test list_customers works for Vendedor with require_admin_or_vendedor
        allowed_vendedor = require_admin_or_vendedor(vendedor_user)
        assert allowed_vendedor.id == vendedor_user.id
        customers_result = list_customers(database=db, _=vendedor_user)
        assert isinstance(customers_result, list)

        print("test_vendedor_role_and_category_commission passed successfully!")
    finally:
        if vendedor_user and vendedor_user.id:
            db.delete(vendedor_user)
        if admin_user and admin_user.id:
            db.delete(admin_user)
        if test_cat and test_cat.id:
            db.delete(test_cat)
        db.commit()
        db.close()


if __name__ == "__main__":
    test_vendedor_role_and_category_commission()
