#!/usr/bin/env python
"""Script para crear un administrador sin interacción."""
import sys
sys.path.insert(0, "/c/Proyectos/Repos-account-aws/pedidos.distribuidoratridente.cl/backend")

from sqlalchemy import select
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.entities import Rol, Usuario

ADMIN_ROLE = "ADMINISTRADOR"

def create_admin(name: str, email: str, password: str) -> None:
    with SessionLocal() as database:
        existing_user = database.scalar(select(Usuario).where(Usuario.correo == email))
        if existing_user:
            print(f"Usuario {email} ya existe")
            return

        role = database.scalar(select(Rol).where(Rol.nombre == ADMIN_ROLE))
        if not role:
            role = Rol(nombre=ADMIN_ROLE)
            database.add(role)
            database.flush()

        database.add(
            Usuario(
                nombre=name,
                correo=email,
                password_hash=hash_password(password),
                rol_id=role.id,
                activo=True,
            )
        )
        database.commit()

    print(f"Administrador creado: {email}")

if __name__ == "__main__":
    create_admin("Administrador", "admin@distribuidoratridente.cl", "admin123456")
