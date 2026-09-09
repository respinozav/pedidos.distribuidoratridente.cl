from uuid import uuid4
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import SessionLocal
from app.core.security import hash_password, verify_password
from app.models.entities import Rol, Usuario
from app.schemas.dto import AdminPasswordUpdate, AdminProfileUpdate
from app.controllers.routes import admin_profile, update_admin_profile, update_admin_password


def test_admin_profile_workflow():
    db = SessionLocal()
    test_user = None
    try:
        # Get or create an active role
        role = db.scalar(select(Rol).where(Rol.activo.is_(True)))
        if not role:
            role = Rol(nombre=f"RolTest-{uuid4().hex[:6]}", activo=True)
            db.add(role)
            db.commit()
            db.refresh(role)

        initial_password = "InitialPassword123!"
        unique_email = f"admin_test_{uuid4().hex[:8]}@tridente.cl"
        test_user = Usuario(
            nombre="Admin Tester",
            correo=unique_email,
            password_hash=hash_password(initial_password),
            rol_id=role.id,
            activo=True,
            celular="+56911223344",
            recibe_pedido=False,
        )
        db.add(test_user)
        db.commit()
        db.refresh(test_user, attribute_names=["rol"])

        # 1. Test admin_profile (GET)
        profile = admin_profile(database=db, current_admin=test_user)
        assert profile is not None
        assert profile.id == test_user.id
        assert profile.nombre == "Admin Tester"
        assert profile.correo == unique_email
        assert profile.celular == "+56911223344"
        assert profile.rol is not None
        assert profile.rol.id == role.id

        # 2. Test update_admin_profile (PUT)
        update_dto = AdminProfileUpdate(nombre="Admin Tester Modificado", celular="+56999887766")
        updated = update_admin_profile(payload=update_dto, database=db, current_admin=test_user)
        assert updated.nombre == "Admin Tester Modificado"
        assert updated.celular == "+56999887766"

        # Verify persisted in database
        db_user = db.scalar(select(Usuario).where(Usuario.id == test_user.id))
        assert db_user.nombre == "Admin Tester Modificado"
        assert db_user.celular == "+56999887766"

        # 3. Test update_admin_password (PUT) - invalid current password
        bad_pwd_dto = AdminPasswordUpdate(
            current_password="WrongPassword123!",
            new_password="NewSecretPassword123!",
        )
        try:
            update_admin_password(payload=bad_pwd_dto, database=db, current_admin=test_user)
            assert False, "Should have raised HTTPException 400 for incorrect current password"
        except HTTPException as exc:
            assert exc.status_code == 400
            assert "contraseña actual es incorrecta" in exc.detail

        # 4. Test update_admin_password (PUT) - valid current password
        valid_pwd_dto = AdminPasswordUpdate(
            current_password=initial_password,
            new_password="NewSecretPassword123!",
        )
        update_admin_password(payload=valid_pwd_dto, database=db, current_admin=test_user)

        # Verify password hash updated and works
        db.refresh(test_user)
        assert verify_password("NewSecretPassword123!", test_user.password_hash)
        assert not verify_password(initial_password, test_user.password_hash)

    finally:
        if test_user and test_user.id:
            try:
                db.delete(test_user)
                db.commit()
            except Exception:
                db.rollback()
        db.close()
