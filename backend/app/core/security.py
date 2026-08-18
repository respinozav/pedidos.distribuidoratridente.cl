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
    minutes = expires_minutes if expires_minutes is not None and expires_minutes > 0 else settings.jwt_access_token_expire_minutes
    expires_at = datetime.now(UTC) + timedelta(minutes=minutes)
    return jwt.encode(
        {"sub": str(user_id), "role": role, "exp": expires_at},
        get_jwt_secret(),
        algorithm=settings.jwt_algorithm,
    )


def create_customer_access_token(customer_id: UUID, expires_minutes: int | None = None) -> str:
    return create_access_token(customer_id, "CLIENTE", expires_minutes=expires_minutes)