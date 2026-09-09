from uuid import uuid4
from fastapi import HTTPException
from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.entities import Rol, Usuario
from app.api.dependencies import require_super_admin
from app.controllers.routes import admin_profile


def test_colaborador_role_permissions():
    db = SessionLocal()
    colab_user = None
    admin_user = None
    try:
        # 1. Verify COLABORADOR and ADMINISTRADOR roles exist
        colab_role = db.scalar(select(Rol).where(Rol.nombre == "COLABORADOR"))
        assert colab_role is not None, "Role COLABORADOR must exist in database"
        assert colab_role.activo is True

        admin_role = db.scalar(select(Rol).where(Rol.nombre == "ADMINISTRADOR"))
        assert admin_role is not None, "Role ADMINISTRADOR must exist in database"
        assert admin_role.activo is True

        # 2. Create a test Colaborador user
        colab_email = f"colab_test_{uuid4().hex[:8]}@tridente.cl"
        colab_user = Usuario(
            nombre="Colaborador Tester",
            correo=colab_email,
            password_hash=hash_password("ColabPass123!"),
            rol_id=colab_role.id,
            activo=True,
            celular="+56911223344",
            recibe_pedido=False,
        )
        db.add(colab_user)

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
        db.refresh(colab_user, attribute_names=["rol"])
        db.refresh(admin_user, attribute_names=["rol"])

        # 3. Test require_super_admin with Colaborador -> must raise 403 Forbidden
        try:
            require_super_admin(colab_user)
            assert False, "require_super_admin should have raised HTTPException 403 for COLABORADOR"
        except HTTPException as exc:
            assert exc.status_code == 403
            assert "administradores" in exc.detail.lower()

        # 4. Test require_super_admin with Admin -> must succeed
        allowed_admin = require_super_admin(admin_user)
        assert allowed_admin.id == admin_user.id

        # 5. Test admin_profile works for Colaborador
        profile = admin_profile(database=db, current_admin=colab_user)
        assert profile is not None
        assert profile.id == colab_user.id
        assert profile.rol.nombre == "COLABORADOR"

        print("test_colaborador_role_permissions passed!")
    finally:
        if colab_user and colab_user.id:
            db.delete(colab_user)
        if admin_user and admin_user.id:
            db.delete(admin_user)
        db.commit()
        db.close()


if __name__ == "__main__":
    test_colaborador_role_permissions()
