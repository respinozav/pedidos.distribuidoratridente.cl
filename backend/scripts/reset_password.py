import argparse
from getpass import getpass

from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.entities import Usuario


def reset_password(email: str) -> None:
    password = getpass("Nueva contrasena: ")
    confirmation = getpass("Confirmar nueva contrasena: ")
    if password != confirmation:
        raise ValueError("Las contrasenas no coinciden")
    if len(password) < 8:
        raise ValueError("La contrasena debe tener al menos 8 caracteres")

    with SessionLocal() as database:
        user = database.scalar(select(Usuario).where(Usuario.correo == email))
        if not user:
            raise ValueError("No existe un usuario con ese correo")
        user.password_hash = hash_password(password)
        database.commit()

    print(f"Contrasena actualizada: {email}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Restablece la contrasena de un usuario.")
    parser.add_argument("--email", required=True, help="Correo del usuario")
    arguments = parser.parse_args()
    reset_password(arguments.email)