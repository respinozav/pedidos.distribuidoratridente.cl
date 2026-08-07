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


def create_access_token(user_id: UUID, role: str) -> str:
    expires_at = datetime.now(UTC) + timedelta(minutes=settings.jwt_access_token_expire_minutes)
    return jwt.encode(
        {"sub": str(user_id), "role": role, "exp": expires_at},
        get_jwt_secret(),
        algorithm=settings.jwt_algorithm,
    )


def create_customer_access_token(customer_id: UUID) -> str:
    return create_access_token(customer_id, "CLIENTE")