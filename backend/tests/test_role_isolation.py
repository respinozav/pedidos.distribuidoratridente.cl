"""
Tests automatizados para verificar el aislamiento estricto de roles (RBAC)
y la protección de módulos del Administrador e Inteligencia Artificial
frente a usuarios con rol CLIENTE.
"""

from pathlib import Path
import sys
from uuid import uuid4
from types import SimpleNamespace
from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.api.dependencies import (
    get_current_admin,
    get_current_customer,
    require_super_admin,
    require_not_vendedor,
)
from app.core.security import create_access_token


class MockDatabase:
    def __init__(self, user=None, customer=None):
        self._user = user
        self._customer = customer

    def scalar(self, statement):
        return self._user

    def get(self, entity_class, entity_id):
        return self._customer


def test_customer_token_rejected_by_admin_dependency():
    """Un token emitido para CLIENTE debe ser rechazado categóricamente con 403 por get_current_admin."""
    customer_id = uuid4()
    customer_token = create_access_token(customer_id, role="CLIENTE")
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=customer_token)
    db = MockDatabase()

    raised = False
    try:
        get_current_admin(creds, db)
    except HTTPException as exc:
        raised = True
        assert exc.status_code == status.HTTP_403_FORBIDDEN
        assert "Acceso denegado" in exc.detail
    assert raised, "Se esperaba HTTPException 403 pero no se levantó excepción"


def test_purged_user_rejected_by_admin_dependency():
    """Un usuario que ya no existe en la base de datos (purgado) debe ser rechazado con 401."""
    user_id = uuid4()
    admin_token = create_access_token(user_id, role="ADMINISTRADOR")
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=admin_token)
    db = MockDatabase(user=None)  # No existe en la base de datos

    raised = False
    try:
        get_current_admin(creds, db)
    except HTTPException as exc:
        raised = True
        assert exc.status_code == status.HTTP_401_UNAUTHORIZED
    assert raised, "Se esperaba HTTPException 401 pero no se levantó excepción"


def test_admin_with_cliente_role_rejected():
    """Si por error un usuario en la BD tiene rol CLIENTE, get_current_admin debe rechazarlo con 403."""
    user_id = uuid4()
    admin_token = create_access_token(user_id, role="ADMINISTRADOR")
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=admin_token)
    fake_user = SimpleNamespace(
        id=user_id,
        activo=True,
        rol=SimpleNamespace(nombre="CLIENTE"),
    )
    db = MockDatabase(user=fake_user)

    raised = False
    try:
        get_current_admin(creds, db)
    except HTTPException as exc:
        raised = True
        assert exc.status_code == status.HTTP_403_FORBIDDEN
    assert raised, "Se esperaba HTTPException 403 pero no se levantó excepción"


def test_require_super_admin_rejects_non_admin():
    """require_super_admin debe rechazar a colaboradores y vendedores."""
    colab_user = SimpleNamespace(
        id=uuid4(),
        activo=True,
        rol=SimpleNamespace(nombre="COLABORADOR"),
    )
    raised = False
    try:
        require_super_admin(colab_user)
    except HTTPException as exc:
        raised = True
        assert exc.status_code == status.HTTP_403_FORBIDDEN
    assert raised, "Se esperaba HTTPException 403 pero no se levantó excepción"


def test_require_not_vendedor_rejects_vendedor():
    """require_not_vendedor debe rechazar a usuarios con rol VENDEDOR."""
    vendedor_user = SimpleNamespace(
        id=uuid4(),
        activo=True,
        rol=SimpleNamespace(nombre="VENDEDOR"),
    )
    raised = False
    try:
        require_not_vendedor(vendedor_user)
    except HTTPException as exc:
        raised = True
        assert exc.status_code == status.HTTP_403_FORBIDDEN
    assert raised, "Se esperaba HTTPException 403 pero no se levantó excepción"


def test_get_current_customer_rejects_admin_token():
    """get_current_customer debe rechazar tokens administrativos que no tengan role='CLIENTE'."""
    admin_token = create_access_token(uuid4(), role="ADMINISTRADOR")
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=admin_token)
    db = MockDatabase()

    raised = False
    try:
        get_current_customer(creds, db)
    except HTTPException as exc:
        raised = True
        assert exc.status_code == status.HTTP_401_UNAUTHORIZED
    assert raised, "Se esperaba HTTPException 401 pero no se levantó excepción"


if __name__ == "__main__":
    test_customer_token_rejected_by_admin_dependency()
    test_purged_user_rejected_by_admin_dependency()
    test_admin_with_cliente_role_rejected()
    test_require_super_admin_rejects_non_admin()
    test_require_not_vendedor_rejects_vendedor()
    test_get_current_customer_rejects_admin_token()
    print(">>> TODOS LOS TESTS DE AISLAMIENTO DE ROLES PASARON EXITOSAMENTE! <<<")
