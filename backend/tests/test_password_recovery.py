import sys
from datetime import datetime, timedelta, UTC
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import uuid4

import jwt
from fastapi import HTTPException

# Ensure backend directory is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.security import (
    create_customer_password_reset_token,
    decode_customer_password_reset_token,
    get_jwt_secret,
    hash_password,
    settings,
    verify_password,
)
from app.schemas.dto import CustomerPasswordResetConfirm, CustomerPasswordResetRequest
from app.controllers.routes import (
    request_customer_password_reset,
    reset_customer_password,
)
from app.models.entities import Cliente


def test_token_generation_and_decoding():
    client_id = uuid4()
    token = create_customer_password_reset_token(client_id, expires_minutes=15)
    assert token is not None

    decoded_id = decode_customer_password_reset_token(token)
    assert decoded_id == client_id


def test_expired_token_rejected():
    client_id = uuid4()
    token = create_customer_password_reset_token(client_id, expires_minutes=-1)
    try:
        decode_customer_password_reset_token(token)
        assert False, "Debería haber fallado por token caducado"
    except ValueError as e:
        assert "caducado" in str(e).lower()


def test_tampered_token_rejected():
    client_id = uuid4()
    token = create_customer_password_reset_token(client_id, expires_minutes=15)
    tampered = token[:-5] + "XXXXX"
    try:
        decode_customer_password_reset_token(tampered)
        assert False, "Debería haber fallado por token alterado"
    except ValueError as e:
        assert "inválido" in str(e).lower()


def test_wrong_role_token_rejected():
    client_id = uuid4()
    token = jwt.encode(
        {
            "sub": str(client_id),
            "role": "ADMIN",
            "purpose": "password_reset",
            "iat": int(datetime.now(UTC).timestamp()),
            "exp": datetime.now(UTC) + timedelta(minutes=15),
        },
        get_jwt_secret(),
        algorithm=settings.jwt_algorithm,
    )
    try:
        decode_customer_password_reset_token(token)
        assert False, "Debería haber fallado por rol no cliente"
    except ValueError as e:
        assert "portal de clientes" in str(e).lower()


def test_wrong_purpose_token_rejected():
    client_id = uuid4()
    token = jwt.encode(
        {
            "sub": str(client_id),
            "role": "CLIENTE",
            "purpose": "session_login",
            "iat": int(datetime.now(UTC).timestamp()),
            "exp": datetime.now(UTC) + timedelta(minutes=15),
        },
        get_jwt_secret(),
        algorithm=settings.jwt_algorithm,
    )
    try:
        decode_customer_password_reset_token(token)
        assert False, "Debería haber fallado por propósito distinto"
    except ValueError as e:
        assert "recuperación" in str(e).lower()


def test_request_password_reset_anti_enumeration():
    db_mock = MagicMock()
    # No customer found
    db_mock.scalar.return_value = None

    req_mock = MagicMock()
    req_mock.client.host = "127.0.0.1"
    req_mock.headers.get.return_value = "https://pedidos.distribuidoratridente.cl"

    payload = CustomerPasswordResetRequest(correo="noexiste@ejemplo.cl")

    with patch("app.controllers.routes.record_session_log"):
        res = request_customer_password_reset(payload, req_mock, db_mock)
        assert "recibirás un enlace" in res.message


def test_request_password_reset_success():
    client_id = uuid4()
    mock_customer = MagicMock(spec=Cliente)
    mock_customer.id = client_id
    mock_customer.nombre = "Cliente Test"
    mock_customer.correo = "test@cliente.cl"
    mock_customer.activo = True

    db_mock = MagicMock()
    db_mock.scalar.return_value = mock_customer

    req_mock = MagicMock()
    req_mock.client.host = "127.0.0.1"
    req_mock.headers.get.return_value = "https://pedidos.distribuidoratridente.cl"

    payload = CustomerPasswordResetRequest(correo="test@cliente.cl")

    with patch("app.controllers.routes.send_customer_password_reset_email", return_value=True) as mock_send, \
         patch("app.controllers.routes.record_session_log"):
        res = request_customer_password_reset(payload, req_mock, db_mock)
        assert "recibirás un enlace" in res.message
        assert mock_send.called
        # Verify the token passed to email is valid
        call_kwargs = mock_send.call_args.kwargs
        token = call_kwargs["reset_token"]
        assert decode_customer_password_reset_token(token) == client_id


def test_reset_password_success():
    client_id = uuid4()
    mock_customer = MagicMock(spec=Cliente)
    mock_customer.id = client_id
    mock_customer.nombre = "Cliente Test"
    mock_customer.correo = "test@cliente.cl"
    mock_customer.activo = True
    mock_customer.password_hash = hash_password("oldpassword123")

    db_mock = MagicMock()
    db_mock.scalar.return_value = mock_customer

    req_mock = MagicMock()
    req_mock.client.host = "127.0.0.1"
    req_mock.headers.get.return_value = None

    token = create_customer_password_reset_token(client_id, expires_minutes=15)
    payload = CustomerPasswordResetConfirm(token=token, nueva_contrasena="newpassword456")

    with patch("app.controllers.routes.notify_customer_password_changed") as mock_notify, \
         patch("app.controllers.routes.record_session_log"):
        res = reset_customer_password(payload, req_mock, db_mock)
        assert "restablecida exitosamente" in res.message
        assert verify_password("newpassword456", mock_customer.password_hash)
        assert mock_notify.called
        assert db_mock.commit.called


def test_reset_password_invalid_token():
    db_mock = MagicMock()
    req_mock = MagicMock()
    req_mock.client.host = "127.0.0.1"
    req_mock.headers.get.return_value = None

    payload = CustomerPasswordResetConfirm(token="invalid_token_123", nueva_contrasena="newpassword456")

    try:
        reset_customer_password(payload, req_mock, db_mock)
        assert False, "Debería haber fallado con 400"
    except HTTPException as exc:
        assert exc.status_code == 400


if __name__ == "__main__":
    test_token_generation_and_decoding()
    print("test_token_generation_and_decoding: OK")
    test_expired_token_rejected()
    print("test_expired_token_rejected: OK")
    test_tampered_token_rejected()
    print("test_tampered_token_rejected: OK")
    test_wrong_role_token_rejected()
    print("test_wrong_role_token_rejected: OK")
    test_wrong_purpose_token_rejected()
    print("test_wrong_purpose_token_rejected: OK")
    test_request_password_reset_anti_enumeration()
    print("test_request_password_reset_anti_enumeration: OK")
    test_request_password_reset_success()
    print("test_request_password_reset_success: OK")
    test_reset_password_success()
    print("test_reset_password_success: OK")
    test_reset_password_invalid_token()
    print("test_reset_password_invalid_token: OK")
    print("\nTODOS LOS TESTS DE RECUPERACIÓN DE CONTRASEÑA PASARON EXITOSAMENTE!")
