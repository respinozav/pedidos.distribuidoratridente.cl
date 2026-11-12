"""Test para verificar campos de notificación Camila en Usuario."""

import sys
from pathlib import Path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

import uuid
from app.models.entities import Usuario, Rol
from app.schemas.dto import UserInput, UserCreate, UserUpdate, UserOutput


def test_user_schemas_include_camila_fields():
    user_input = UserInput(
        nombre="Admin Test",
        correo="admin@distribuidoratridente.cl",
        celular="+56912345678",
        recibe_pedido=True,
        recibe_camila_whatsapp=True,
        recibe_camila_email=True,
        rol_id=uuid.uuid4(),
        activo=True,
    )
    assert user_input.recibe_camila_whatsapp is True
    assert user_input.recibe_camila_email is True

    dumped = user_input.model_dump()
    assert "recibe_camila_whatsapp" in dumped
    assert "recibe_camila_email" in dumped
    assert dumped["recibe_camila_whatsapp"] is True
    assert dumped["recibe_camila_email"] is True


def test_user_entity_model_fields():
    user = Usuario(
        nombre="Admin Camila",
        correo="camila_admin@distribuidoratridente.cl",
        password_hash="fakehash",
        rol_id=uuid.uuid4(),
        celular="56999998888",
        recibe_pedido=False,
        recibe_camila_whatsapp=True,
        recibe_camila_email=False,
    )
    assert user.recibe_camila_whatsapp is True
    assert user.recibe_camila_email is False


if __name__ == "__main__":
    test_user_schemas_include_camila_fields()
    test_user_entity_model_fields()
    print("TODOS LOS TESTS DE CAMPOS CAMILA EN USUARIO PASARON EXITOSAMENTE!")
