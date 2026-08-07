import argparse
from getpass import getpass

from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.entities import Rol, Usuario

ADMIN_ROLE = "ADMINISTRADOR"


def create_admin(name: str, email: str) -> None:
    password = getpass("Contrasena del administrador: ")
    confirmation = getpass("Confirmar contrasena: ")
    if password != confirmation:
        raise ValueError("Las contrasenas no coinciden")
    if len(password) < 8:
        raise ValueError("La contrasena debe tener al menos 8 caracteres")

    with SessionLocal() as database:
        existing_user = database.scalar(select(Usuario).where(Usuario.correo == email))
        if existing_user:
            raise ValueError("Ya existe un usuario con ese correo")

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
    parser = argparse.ArgumentParser(description="Crea el administrador inicial de Distribuidora Tridente.")
    parser.add_argument("--name", required=True, help="Nombre del administrador")
    parser.add_argument("--email", required=True, help="Correo del administrador")
    arguments = parser.parse_args()
    create_admin(arguments.name, arguments.email)