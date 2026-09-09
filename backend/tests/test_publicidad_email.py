import uuid
from decimal import Decimal
from unittest.mock import MagicMock, patch

from app.models.entities import Cliente, Producto, Publicidad
from app.schemas.dto import SendPublicidadEmailInput
from app.services.notifications import build_publicidad_email_html, send_publicidad_campaign


def test_build_publicidad_email_html():
    cli = Cliente(
        id=uuid.uuid4(),
        nombre="ALMACÉN DON PEPE",
        correo="donpepe@almacen.cl",
        rut="76.123.456-7",
    )
    prod = Producto(
        id=uuid.uuid4(),
        codigo="GAL-001",
        nombre="GALLETAS CHOCOLATE 100G",
        precio=Decimal("850"),
        cantidad=100,
        activo=True,
    )
    pub = Publicidad(
        id=uuid.uuid4(),
        titulo="OFERTAZO DE LANZAMIENTO",
        subtitulo="Aprovecha antes de que se agoten las unidades",
        etiqueta_1="DESTACADO",
        etiqueta_roja="OFERTA",
        texto_boton="Comprar Ahora en el Catálogo",
        color_fondo="#082620",
        producto=prod,
    )

    html_out = build_publicidad_email_html(
        publicidad=pub,
        cliente=cli,
        mensaje_adicional="Estimado socio comercial, tenemos precios especiales por esta semana.",
    )

    assert "ALMACÉN DON PEPE" in html_out
    assert "OFERTAZO DE LANZAMIENTO" in html_out
    assert "Aprovecha antes de que se agoten" in html_out
    assert "Comprar Ahora en el Catálogo" in html_out
    assert "precios especiales por esta semana" in html_out
    assert "GALLETAS CHOCOLATE 100G" in html_out
    assert "GAL-001" in html_out
    assert "donpepe@almacen.cl" in html_out


def test_send_publicidad_campaign_copia_oculta_mock():
    cli1 = Cliente(id=uuid.uuid4(), nombre="Cliente 1", correo="cli1@test.com")
    cli2 = Cliente(id=uuid.uuid4(), nombre="Cliente 2", correo="cli2@test.com")
    pub = Publicidad(
        id=uuid.uuid4(),
        titulo="PROMO VERANO",
        subtitulo="Descuentos en confites",
        color_fondo="#2c2203",
    )

    sent_messages = []

    class FakeSMTP:
        def __init__(self, *args, **kwargs):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def login(self, user, pwd):
            pass
        def send_message(self, msg):
            sent_messages.append(msg)
        def quit(self):
            pass

    mock_db = MagicMock()

    with patch("app.services.notifications._get_smtp_settings", return_value={
        "configured": True,
        "host": "mail.test.com",
        "port": 465,
        "username": "notif@test.com",
        "password": "secretpassword",
        "from_name": "Distribuidora Tridente",
        "from_email": "notif@test.com",
    }), patch("smtplib.SMTP_SSL", FakeSMTP):
        res = send_publicidad_campaign(
            publicidad=pub,
            clientes=[cli1, cli2],
            asunto="Super Oferta Semanal",
            mensaje_adicional="No te pierdas esta promo",
            database=mock_db,
        )

    assert res["total_destinatarios"] == 2
    assert res["enviados"] == 2
    assert res["fallidos"] == 0
    assert len(sent_messages) == 2

    # Verificación de COPIA OCULTA (cada cliente recibe su mensaje independiente, To privado)
    assert sent_messages[0]["To"] == "Cliente 1 <cli1@test.com>"
    assert "cli2@test.com" not in sent_messages[0]["To"]

    assert sent_messages[1]["To"] == "Cliente 2 <cli2@test.com>"
    assert "cli1@test.com" not in sent_messages[1]["To"]


def test_publicidad_email_input_dto():
    dto = SendPublicidadEmailInput(
        asunto="Novedades del mes",
        mensaje_adicional="Revisa los productos destacados",
        todos=True,
    )
    assert dto.asunto == "Novedades del mes"
    assert dto.todos is True
    assert dto.cliente_ids == []


# Aliases for test runners
test_publicidad_email_dto = test_publicidad_email_input_dto
test_publicidad_html_builder = test_build_publicidad_email_html
test_send_publicidad_campaign_isolated_bcc = test_send_publicidad_campaign_copia_oculta_mock


if __name__ == "__main__":
    test_build_publicidad_email_html()
    test_send_publicidad_campaign_copia_oculta_mock()
    test_publicidad_email_input_dto()
    print(">>> test_publicidad_email PASSED! <<<")
