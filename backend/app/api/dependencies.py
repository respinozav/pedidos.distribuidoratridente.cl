from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import get_jwt_secret
from app.models.entities import Cliente, Usuario

bearer_scheme = HTTPBearer()
settings = get_settings()
DatabaseSession = Annotated[Session, Depends(get_db)]


def get_current_admin(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
    database: DatabaseSession,
) -> Usuario:
    try:
        payload = jwt.decode(credentials.credentials, get_jwt_secret(), algorithms=[settings.jwt_algorithm])
        user_id = UUID(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError) as error:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token invalido") from error
    user = database.get(Usuario, user_id)
    if not user or not user.activo:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Usuario no autorizado")
    return user


AdminUser = Annotated[Usuario, Depends(get_current_admin)]


def get_current_customer(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
    database: DatabaseSession,
) -> Cliente:
    try:
        payload = jwt.decode(credentials.credentials, get_jwt_secret(), algorithms=[settings.jwt_algorithm])
        customer_id = UUID(payload["sub"])
        if payload.get("role") != "CLIENTE":
            raise ValueError("Rol de cliente requerido")
    except (jwt.PyJWTError, KeyError, ValueError) as error:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token invalido") from error
    customer = database.get(Cliente, customer_id)
    if not customer or not customer.activo:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Cliente no autorizado")
    return customer


CustomerUser = Annotated[Cliente, Depends(get_current_customer)]


def get_current_user_or_customer(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
    database: DatabaseSession,
) -> tuple[UUID, str]:
    try:
        payload = jwt.decode(credentials.credentials, get_jwt_secret(), algorithms=[settings.jwt_algorithm])
        subject_id = UUID(payload["sub"])
        role = payload.get("role", "ADMIN")
    except (jwt.PyJWTError, KeyError, ValueError) as error:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token invalido") from error

    if role == "CLIENTE":
        customer = database.get(Cliente, subject_id)
        if not customer or not customer.activo:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Cliente no autorizado")
        return subject_id, "CLIENTE"
    else:
        user = database.get(Usuario, subject_id)
        if not user or not user.activo:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Usuario no autorizado")
        return subject_id, user.rol.nombre if user.rol else "ADMIN"


AuthSubject = Annotated[tuple[UUID, str], Depends(get_current_user_or_customer)]
