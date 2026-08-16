import html
import logging
import smtplib
from datetime import datetime
from decimal import Decimal
from email.message import EmailMessage
from io import BytesIO
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.entities import Cliente, Pedido, Rol, Usuario

logger = logging.getLogger(__name__)
LOGO_PATH = Path(__file__).resolve().parents[2] / "assets" / "logo_tridente.png"


def _currency(value: Decimal) -> str:
    return f"${value:,.0f}".replace(",", ".")


def _product_detail_label(detail: object) -> str:
    name = html.escape(getattr(detail, "nombre_producto", ""))
    code = html.escape(getattr(detail, "codigo_producto", ""))
    if code:
        return f"<b>{name}</b> <font color='#667085'>[{code}]</font>"
    return f"<b>{name}</b>"


def _get_smtp_settings(database: Session | None = None) -> dict[str, object]:
    if database is not None and hasattr(database, "query"):
        try:
            from app.repositories.system_settings_repository import SystemSettingsRepository

            repo = SystemSettingsRepository()
            db_settings = repo.get_settings(database)
            if (
                db_settings.smtp_host
                and db_settings.smtp_username
                and db_settings.smtp_password
                and db_settings.smtp_from_email
            ):
                return {
                    "configured": True,
                    "host": db_settings.smtp_host,
                    "port": db_settings.smtp_port or 465,
                    "username": db_settings.smtp_username,
                    "password": db_settings.smtp_password,
                    "from_name": db_settings.smtp_from_name or "Distribuidora Tridente",
                    "from_email": db_settings.smtp_from_email,
                }
        except Exception:
            logger.warning("No se pudo leer la configuración SMTP de la base de datos, usando fallback de entorno")

    env_settings = get_settings()
    return {
        "configured": env_settings.smtp_configured,
        "host": env_settings.smtp_host,
        "port": env_settings.smtp_port,
        "username": env_settings.smtp_username,
        "password": env_settings.smtp_password,
        "from_name": env_settings.smtp_from_name,
        "from_email": env_settings.smtp_from_email,
    }


def notify_customer_password_changed(customer: Cliente, database: Session | None = None) -> None:
    if database is None:
        try:
            from app.core.database import SessionLocal

            with SessionLocal() as db_session:
                smtp_config = _get_smtp_settings(db_session)
        except Exception:
            smtp_config = _get_smtp_settings(None)
    else:
        smtp_config = _get_smtp_settings(database)

    recipient = (customer.correo or "").strip()
    if not smtp_config["configured"] or not recipient:
        return
    message = EmailMessage()
    message["Subject"] = "Cambio de contraseña | Distribuidora Tridente"
    message["From"] = f"{smtp_config['from_name']} <{smtp_config['from_email']}>"
    message["To"] = recipient
    message.set_content("Tu contraseña fue actualizada correctamente. Si no realizaste este cambio, comunícate con Distribuidora Tridente.")
    message.add_alternative(
        """<html><body style='margin:0;background:#f4f7fb;font-family:Segoe UI,Arial,sans-serif;color:#172b4d'>
<div style='max-width:680px;margin:24px auto;background:#ffffff;border:1px solid #d9e2ec'>
<div style='padding:28px 32px;background:#102a43;color:#ffffff'><div style='font-size:22px;font-weight:700'>Distribuidora Tridente</div><div style='margin-top:8px;color:#9bceff;font-size:12px;font-weight:700;letter-spacing:1px'>SEGURIDAD DE TU CUENTA</div></div>
<div style='padding:28px 32px'><h1 style='font-size:21px;margin-top:0'>Tu contraseña fue actualizada</h1><p>Confirmamos que la contraseña de tu cuenta fue cambiada correctamente.</p><p style='color:#667085'>Si no realizaste este cambio, comunícate con Distribuidora Tridente de inmediato.</p></div></div></body></html>""",
        subtype="html",
    )
    try:
        with smtplib.SMTP_SSL(smtp_config["host"], smtp_config["port"], timeout=20) as smtp:
            smtp.login(smtp_config["username"], smtp_config["password"])
            smtp.send_message(message)
    except (OSError, smtplib.SMTPException):
        logger.exception("No fue posible enviar el acuse de cambio de contraseña al cliente %s", customer.id)


def _order_pdf(order: Pedido) -> bytes:
    customer_name = order.cliente.nombre or order.cliente.rut or order.cliente.celular or "Cliente"
    customer_id = order.cliente.rut or order.cliente.celular or "Sin identificador"
    customer_email = order.cliente.correo or "Sin correo"
    customer_phone = order.cliente.celular or "Sin teléfono"
    address = ", ".join(part for part in (order.direccion.direccion, order.direccion.comuna) if part)
    order_code = str(order.id).split("-")[0].upper()
    created_at = order.created_at.astimezone().strftime("%d-%m-%Y %H:%M") if order.created_at else "-"
    output = BytesIO()
    document = SimpleDocTemplate(output, pagesize=A4, rightMargin=18 * mm, leftMargin=18 * mm, topMargin=18 * mm, bottomMargin=18 * mm)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Brand", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=20, textColor=colors.HexColor("#172B4D"), leading=24))
    styles.add(ParagraphStyle(name="OrderCode", parent=styles["Normal"], alignment=TA_RIGHT, fontName="Helvetica-Bold", fontSize=14, textColor=colors.HexColor("#172B4D")))
    styles.add(ParagraphStyle(name="Details", parent=styles["Normal"], fontSize=9, leading=12, textColor=colors.HexColor("#334E68")))
    styles.add(ParagraphStyle(name="ProductCell", parent=styles["Normal"], fontSize=9, leading=11, textColor=colors.HexColor("#334E68")))
    story = []
    brand = Image(str(LOGO_PATH), width=45 * mm, height=30 * mm, kind="proportional") if LOGO_PATH.is_file() else Paragraph("Distribuidora Tridente", styles["Brand"])
    header = Table([[brand, Paragraph(f"PEDIDO #{order_code}", styles["OrderCode"])]], colWidths=[95 * mm, 79 * mm])
    header.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LINEBELOW", (0, 0), (-1, -1), 1.2, colors.HexColor("#D44B58")), ("BOTTOMPADDING", (0, 0), (-1, -1), 10)]))
    story.extend([header, Spacer(1, 8 * mm)])
    customer_details = "<br/>".join((
        f"<b>Cliente:</b> {html.escape(customer_name)}",
        f"<b>Identificador:</b> {html.escape(customer_id)}",
        f"<b>Correo:</b> {html.escape(customer_email)}",
        f"<b>Teléfono:</b> {html.escape(customer_phone)}",
        f"<b>Fecha del pedido:</b> {created_at}",
        f"<b>Dirección de despacho:</b> {html.escape(address or 'Sin dirección registrada')}",
    ))
    story.extend([Paragraph(customer_details, styles["Details"]), Spacer(1, 7 * mm)])
    rows = [["Producto", "Cantidad", "Precio", "Subtotal"]]
    for detail in order.detalles:
        product = Paragraph(_product_detail_label(detail), styles["ProductCell"])
        rows.append([product, str(detail.cantidad), _currency(detail.precio_unitario), _currency(detail.subtotal)])
    details = Table(rows, colWidths=[87 * mm, 24 * mm, 31 * mm, 32 * mm], repeatRows=1)
    details.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EAF4FF")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#334E68")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#D9E2EC")),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]))
    total = Table([["TOTAL", _currency(order.total)]], colWidths=[135 * mm, 39 * mm], hAlign="RIGHT")
    total.setStyle(TableStyle([("TOPPADDING", (0, 0), (-1, -1), 10), ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 13), ("ALIGN", (1, 0), (1, 0), "RIGHT"), ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#172B4D"))]))
    story.extend([details, total])
    document.build(story)
    return output.getvalue()


def _build_order_message(
    order: Pedido,
    recipient: str,
    subject: str,
    heading: str,
    introduction: str,
    include_customer_data: bool,
    from_name: str | None = None,
    from_email: str | None = None,
) -> EmailMessage:
    settings = get_settings()
    sender_name = from_name or settings.smtp_from_name
    sender_email = from_email or settings.smtp_from_email
    order_code = str(order.id).split("-")[0].upper()
    customer_name = order.cliente.nombre or order.cliente.rut or order.cliente.celular or "Cliente"
    customer_id = order.cliente.rut or order.cliente.celular or "Sin identificador"
    customer_email = order.cliente.correo or "Sin correo"
    customer_phone = order.cliente.celular or "Sin teléfono"
    address = ", ".join(part for part in (order.direccion.direccion, order.direccion.comuna) if part) or "Sin dirección"
    detail_rows = "".join(
        f"<tr><td style='padding:8px 10px;border-top:1px solid #d9e2ec'><strong>{html.escape(detail.nombre_producto)}</strong> <span style='color:#667085;font-size:12px'>[{html.escape(detail.codigo_producto)}]</span></td><td style='padding:8px 10px;border-top:1px solid #d9e2ec;text-align:center'>{detail.cantidad}</td><td style='padding:8px 10px;border-top:1px solid #d9e2ec;text-align:right'>{_currency(detail.precio_unitario)}</td><td style='padding:8px 10px;border-top:1px solid #d9e2ec;text-align:right'>{_currency(detail.subtotal)}</td></tr>"
        for detail in order.detalles
    )
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = f"{sender_name} <{sender_email}>"
    message["To"] = recipient
    message.set_content(f"Pedido #{order_code}. Total: {_currency(order.total)}.")
    customer_block = (
        f"<div style='padding:16px;background:#eaf4ff;border-left:4px solid #146cce'><strong>{html.escape(customer_name)}</strong><br><span style='color:#667085'>{html.escape(customer_id)} · {html.escape(customer_phone)} · {html.escape(customer_email)}<br>{html.escape(address)}</span></div>"
        if include_customer_data
        else ""
    )
    message.add_alternative(
        f"""<html><body style='margin:0;background:#f4f7fb;font-family:Segoe UI,Arial,sans-serif;color:#172b4d'>
<div style='max-width:680px;margin:24px auto;background:#ffffff;border:1px solid #d9e2ec'>
<div style='padding:28px 32px;background:#102a43;color:#ffffff'><div style='font-size:22px;font-weight:700'>Distribuidora Tridente</div><div style='margin-top:8px;color:#9bceff;font-size:12px;font-weight:700;letter-spacing:1px'>{heading}</div><div style='margin-top:6px;font-size:25px;font-weight:700'>Pedido #{order_code}</div></div>
<div style='padding:28px 32px'><p style='margin-top:0'>{introduction}</p>
{customer_block}
<table style='width:100%;border-collapse:collapse;margin-top:22px'><thead><tr style='background:#f8fafc;color:#667085;font-size:12px;text-align:left'><th style='padding:10px'>Producto</th><th style='padding:10px;text-align:center'>Cant.</th><th style='padding:10px;text-align:right'>Unitario</th><th style='padding:10px;text-align:right'>Subtotal</th></tr></thead><tbody>{detail_rows}</tbody></table>
<div style='margin-top:20px;padding-top:16px;border-top:1px solid #d9e2ec;text-align:right;font-size:19px;font-weight:700'>Total: {_currency(order.total)}</div>
<p style='margin:24px 0 0;color:#667085;font-size:12px'>Se adjunta el comprobante PDF con el detalle del pedido.</p></div></div></body></html>""",
        subtype="html",
    )
    message.add_attachment(_order_pdf(order), maintype="application", subtype="pdf", filename=f"pedido-{order_code}.pdf")
    return message


def notify_administrators_of_order(database: Session, order: Pedido) -> None:
    smtp_config = _get_smtp_settings(database)
    if not smtp_config["configured"]:
        logger.warning("Pedido %s creado sin notificación: SMTP no está configurado", order.id)
        return
    recipients = [
        correo.strip()
        for correo in database.scalars(
            select(Usuario.correo)
            .where(Usuario.activo.is_(True), Usuario.recibe_pedido.is_(True))
        )
        if correo and correo.strip()
    ]
    customer_email = (order.cliente.correo or "").strip()
    messages: list[EmailMessage] = []
    if recipients:
        messages.append(
            _build_order_message(
                order,
                ", ".join(recipients),
                f"Nuevo pedido #{str(order.id).split('-')[0].upper()} | Distribuidora Tridente",
                "NUEVO PEDIDO",
                "Se registró un nuevo pedido y requiere revisión.",
                True,
                from_name=smtp_config["from_name"],
                from_email=smtp_config["from_email"],
            )
        )
    if customer_email:
        messages.append(
            _build_order_message(
                order,
                customer_email,
                f"Confirmación de pedido #{str(order.id).split('-')[0].upper()} | Distribuidora Tridente",
                "PEDIDO CONFIRMADO",
                "Recibimos tu pedido. Te avisaremos cuando su estado cambie.",
                False,
                from_name=smtp_config["from_name"],
                from_email=smtp_config["from_email"],
            )
        )
    if not messages:
        logger.warning("Pedido %s creado sin destinatarios para notificación", order.id)
        return
    try:
        with smtplib.SMTP_SSL(smtp_config["host"], smtp_config["port"], timeout=20) as smtp:
            smtp.login(smtp_config["username"], smtp_config["password"])
            for message in messages:
                smtp.send_message(message)
    except (OSError, smtplib.SMTPException):
        logger.exception("No fue posible notificar el pedido %s", order.id)