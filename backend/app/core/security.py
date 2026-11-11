from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
from passlib.context import CryptContext

from app.core.config import get_settings

password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
settings = get_settings()


def get_jwt_secret() -> str:
    if not settings.jwt_secret_key:
        raise RuntimeError("JWT_SECRET_KEY debe estar configurado para usar autenticacion")
    return settings.jwt_secret_key


def hash_password(password: str) -> str:
    return password_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return password_context.verify(password, password_hash)


def create_access_token(user_id: UUID, role: str, expires_minutes: int | None = None) -> str:
    configured_minutes = expires_minutes if expires_minutes is not None and expires_minutes > 0 else settings.jwt_access_token_expire_minutes
    # Protección: la sesión no debe ser menor a 5 minutos para evitar caducidad inmediata
    minutes = configured_minutes if configured_minutes and configured_minutes >= 5 else 60
    now = datetime.now(UTC)
    expires_at = now + timedelta(minutes=minutes)
    return jwt.encode(
        {
            "sub": str(user_id),
            "role": role,
            "iat": int(now.timestamp()),
            "exp": expires_at,
            "minutes": minutes,
        },
        get_jwt_secret(),
        algorithm=settings.jwt_algorithm,
    )


def create_customer_access_token(customer_id: UUID, expires_minutes: int | None = None) -> str:
    return create_access_token(customer_id, "CLIENTE", expires_minutes=expires_minutes)


def create_vendor_customer_token(
    customer_id: UUID,
    vendedor_id: UUID,
    vendedor_nombre: str,
    expires_minutes: int | None = None,
) -> str:
    configured_minutes = expires_minutes if expires_minutes is not None and expires_minutes > 0 else settings.jwt_access_token_expire_minutes
    minutes = configured_minutes if configured_minutes and configured_minutes >= 5 else 60
    now = datetime.now(UTC)
    expires_at = now + timedelta(minutes=minutes)
    return jwt.encode(
        {
            "sub": str(customer_id),
            "role": "CLIENTE",
            "vendedor_id": str(vendedor_id),
            "vendedor_nombre": vendedor_nombre,
            "iat": int(now.timestamp()),
            "exp": expires_at,
            "minutes": minutes,
        },
        get_jwt_secret(),
        algorithm=settings.jwt_algorithm,
    )


def create_customer_password_reset_token(customer_id: UUID, expires_minutes: int = 15) -> str:
    now = datetime.now(UTC)
    expires_at = now + timedelta(minutes=expires_minutes)
    return jwt.encode(
        {
            "sub": str(customer_id),
            "role": "CLIENTE",
            "purpose": "password_reset",
            "iat": int(now.timestamp()),
            "exp": expires_at,
        },
        get_jwt_secret(),
        algorithm=settings.jwt_algorithm,
    )


def decode_customer_password_reset_token(token: str) -> UUID:
    try:
        payload = jwt.decode(
            token,
            get_jwt_secret(),
            algorithms=[settings.jwt_algorithm],
        )
        if payload.get("role") != "CLIENTE":
            raise ValueError("El enlace no corresponde al portal de clientes.")
        if payload.get("purpose") != "password_reset":
            raise ValueError("El enlace no es válido para recuperación de contraseña.")
        sub = payload.get("sub")
        if not sub:
            raise ValueError("El identificador del cliente es inválido.")
        return UUID(sub)
    except jwt.ExpiredSignatureError:
        raise ValueError("El enlace de recuperación ha caducado (duración máxima 15 minutos). Por favor solicita uno nuevo.")
    except (jwt.PyJWTError, Exception) as exc:
        raise ValueError(f"El enlace de recuperación es inválido o ha sido alterado: {exc}")
