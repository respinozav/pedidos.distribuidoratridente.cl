from unittest.mock import MagicMock, patch
import uuid
from app.models.entities import Cliente, Rol, Usuario
from app.schemas.dto import ProductSuggestionInput, ProductSuggestionOutput
from app.services.notifications import (
    build_product_suggestion_email_html,
    send_product_suggestion_notification,
)


def test_build_product_suggestion_email_html():
    customer = Cliente(
        id=uuid.uuid4(),
        nombre="Minimarket San Jorge",
        rut="76.123.456-7",
        correo="contacto@sanjorge.cl",
        celular="+56912345678",
    )
    producto = "Harina Selecta 1 Kg & Cereal Quaker"
    comentarios = "Nos gustaría formato caja de 10 unidades para reventa."

    html_content = build_product_suggestion_email_html(
        customer=customer,
        producto=producto,
        comentarios=comentarios,
    )

    assert "Minimarket San Jorge" in html_content
    assert "76.123.456-7" in html_content
    assert "contacto@sanjorge.cl" in html_content
    assert "+56912345678" in html_content
    assert "Harina Selecta 1 Kg &amp; Cereal Quaker" in html_content
    assert "Nos gustaría formato caja de 10 unidades" in html_content
    assert "Focus Group" in html_content


def test_send_product_suggestion_notification_success():
    customer = Cliente(
        id=uuid.uuid4(),
        nombre="Almacén Don Tito",
        rut="12.345.678-9",
        correo="dontito@gmail.com",
        celular="+56987654321",
    )
    admin_user = Usuario(
        id=uuid.uuid4(),
        nombre="Administrador General",
        correo="admin@distribuidoratridente.cl",
        activo=True,
    )

    mock_db = MagicMock()
    mock_db.scalars.return_value.all.return_value = [admin_user]

    smtp_config = {
        "configured": True,
        "host": "smtp.gmail.com",
        "port": 465,
        "username": "notificaciones@distribuidoratridente.cl",
        "password": "secretpassword",
        "from_name": "Distribuidora Tridente",
        "from_email": "notificaciones@distribuidoratridente.cl",
    }

    with patch("app.services.notifications._get_smtp_settings", return_value=smtp_config), \
         patch("smtplib.SMTP_SSL") as mock_smtp_ssl:
        mock_server = MagicMock()
        mock_smtp_ssl.return_value.__enter__.return_value = mock_server

        res = send_product_suggestion_notification(
            database=mock_db,
            customer=customer,
            producto="Bebida Monster Mango Loco",
            comentarios="Cajas de 24",
        )

        assert res["success"] is True
        assert res["destinatarios_notificados"] == 1
        mock_server.login.assert_called_once_with("notificaciones@distribuidoratridente.cl", "secretpassword")
        assert mock_server.send_message.called
        assert mock_db.add.called
        assert mock_db.commit.called


def test_send_product_suggestion_no_admins():
    customer = Cliente(
        id=uuid.uuid4(),
        nombre="Almacén Sol",
        rut="11.222.333-4",
    )
    mock_db = MagicMock()
    mock_db.scalars.return_value.all.return_value = []

    res = send_product_suggestion_notification(
        database=mock_db,
        customer=customer,
        producto="Café Dolca 170g",
    )

    assert res["success"] is True
    assert res["destinatarios_notificados"] == 0
    assert mock_db.add.called
    assert mock_db.commit.called


def test_route_submit_product_suggestion():
    from app.controllers.routes import submit_product_suggestion
    customer = Cliente(
        id=uuid.uuid4(),
        nombre="Minimarket Central",
        rut="12.345.678-9",
    )
    mock_db = MagicMock()
    mock_db.scalars.return_value.all.return_value = []

    payload = ProductSuggestionInput(
        producto="Aceite Belmont 1L",
        comentarios="Formato familiar",
    )

    output = submit_product_suggestion(
        payload=payload,
        database=mock_db,
        current_customer=customer,
    )

    assert isinstance(output, ProductSuggestionOutput)
    assert output.success is True


if __name__ == "__main__":
    test_build_product_suggestion_email_html()
    test_send_product_suggestion_notification_success()
    test_send_product_suggestion_no_admins()
    test_route_submit_product_suggestion()
    print("All product suggestion notification tests passed successfully!")
