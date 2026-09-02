import html
import logging
import smtplib
import threading
import time
import traceback
from datetime import datetime
from decimal import Decimal
from email.message import EmailMessage
from io import BytesIO
from pathlib import Path
from uuid import UUID

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.models.entities import Cliente, Pedido, PedidoNotificacionLog, Rol, Usuario

logger = logging.getLogger(__name__)
LOGO_PATH = Path(__file__).resolve().parents[2] / "assets" / "logo_tridente.png"


def _currency(value: Decimal) -> str:
    return f"${value:,.0f}".replace(",", ".")


def _product_detail_label(detail: object) -> str:
    name = html.escape(getattr(detail, "nombre_producto", ""))
    code = html.escape(getattr(detail, "codigo_producto", ""))
    tipo_empaque = getattr(detail, "tipo_empaque", "unidad")
    cant_caja = getattr(detail, "cantidad_caja", None)
    empaque_badge = f" <font color='#146CCE'><b>(Caja x{cant_caja})</b></font>" if tipo_empaque == "caja" and cant_caja else (" <font color='#146CCE'><b>(Caja)</b></font>" if tipo_empaque == "caja" else "")
    if code:
        return f"<b>{name}</b>{empaque_badge} <font color='#667085'>[{code}]</font>"
    return f"<b>{name}</b>{empaque_badge}"



def _create_notification_log(
    database: Session,
    pedido_id: UUID | None,
    canal: str,
    tipo: str,
    destinatario: str,
    estado: str,
    mensaje: str | None = None,
    error: str | None = None,
    duracion_ms: int | None = None,
) -> PedidoNotificacionLog | None:
    """Registra una entrada de log de notificación de manera segura."""
    try:
        log_entry = PedidoNotificacionLog(
            pedido_id=pedido_id,
            canal=canal,
            tipo=tipo,
            destinatario=destinatario,
            estado=estado,
            mensaje=mensaje,
            error=error,
            duracion_ms=duracion_ms,
        )
        database.add(log_entry)
        database.commit()
        return log_entry
    except Exception as e:
        logger.error("No fue posible guardar el log de notificación: %s", e)
        try:
            database.rollback()
        except Exception:
            pass
        return None


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
    header.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LINEBELOW", (0, 0), (-1, -1), 1.2, colors.HexColor("#146CCE")), ("BOTTOMPADDING", (0, 0), (-1, -1), 10)]))
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

    def _is_afecto(detail: object) -> bool:
        if getattr(detail, "afecto", None) is not None:
            return bool(detail.afecto)
        product_obj = getattr(detail, "producto", None)
        if product_obj is not None and getattr(product_obj, "afecto", None) is not None:
            return bool(product_obj.afecto)
        return False

    sorted_detalles = sorted(order.detalles or [], key=lambda d: 0 if _is_afecto(d) else 1)

    rows = [["Producto", "Cantidad", "IVA", "Precio", "Subtotal"]]
    table_styles = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EAF4FF")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#334E68")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (1, 0), (1, -1), "CENTER"),
        ("ALIGN", (2, 0), (2, -1), "CENTER"),
        ("ALIGN", (3, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#D9E2EC")),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]

    for row_idx, detail in enumerate(sorted_detalles, start=1):
        afecto = _is_afecto(detail)
        iva_text = "Afecto" if afecto else "Exento"
        if afecto:
            table_styles.append(("BACKGROUND", (0, row_idx), (-1, row_idx), colors.HexColor("#F0F2F5")))
        product = Paragraph(_product_detail_label(detail), styles["ProductCell"])
        tipo_empaque = getattr(detail, "tipo_empaque", "unidad")
        cant_str = f"{detail.cantidad} cj." if tipo_empaque == "caja" else str(detail.cantidad)
        rows.append([
            product,
            cant_str,
            iva_text,
            _currency(detail.precio_unitario),
            _currency(detail.subtotal),
        ])

    details = Table(rows, colWidths=[74 * mm, 18 * mm, 22 * mm, 28 * mm, 32 * mm], repeatRows=1)
    details.setStyle(TableStyle(table_styles))
    total = Table([["TOTAL", _currency(order.total)]], colWidths=[135 * mm, 39 * mm], hAlign="RIGHT")
    total.setStyle(TableStyle([
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 13),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#172B4D")),
    ]))
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

    def _is_afecto(detail: object) -> bool:
        if getattr(detail, "afecto", None) is not None:
            return bool(detail.afecto)
        product_obj = getattr(detail, "producto", None)
        if product_obj is not None and getattr(product_obj, "afecto", None) is not None:
            return bool(product_obj.afecto)
        return False

    sorted_details = sorted(order.detalles or [], key=lambda d: 0 if _is_afecto(d) else 1)

    def _format_detail_row(detail: object) -> str:
        bg = "background:#f0f2f5;" if _is_afecto(detail) else ""
        tipo_emp = getattr(detail, "tipo_empaque", "unidad")
        cant_caja = getattr(detail, "cantidad_caja", None)
        emp_badge = f" <span style='color:#146CCE;font-weight:600'>(Caja x{cant_caja})</span>" if tipo_emp == "caja" and cant_caja else (" <span style='color:#146CCE;font-weight:600'>(Caja)</span>" if tipo_emp == "caja" else "")
        cant_str = f"{detail.cantidad} cj." if tipo_emp == "caja" else str(detail.cantidad)
        return (
            f"<tr style='{bg}'>"
            f"<td style='padding:8px 10px;border-top:1px solid #d9e2ec'><strong>{html.escape(detail.nombre_producto)}</strong>{emp_badge} <span style='color:#667085;font-size:12px'>[{html.escape(detail.codigo_producto)}]</span></td>"
            f"<td style='padding:8px 10px;border-top:1px solid #d9e2ec;text-align:center'>{cant_str}</td>"
            f"<td style='padding:8px 10px;border-top:1px solid #d9e2ec;text-align:center'>{'Afecto' if _is_afecto(detail) else 'Exento'}</td>"
            f"<td style='padding:8px 10px;border-top:1px solid #d9e2ec;text-align:right'>{_currency(detail.precio_unitario)}</td>"
            f"<td style='padding:8px 10px;border-top:1px solid #d9e2ec;text-align:right'>{_currency(detail.subtotal)}</td>"
            f"</tr>"
        )

    detail_rows = "".join(_format_detail_row(detail) for detail in sorted_details)
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
<table style='width:100%;border-collapse:collapse;margin-top:22px'><thead><tr style='background:#f8fafc;color:#667085;font-size:12px;text-align:left'><th style='padding:10px'>Producto</th><th style='padding:10px;text-align:center'>Cant.</th><th style='padding:10px;text-align:center'>IVA</th><th style='padding:10px;text-align:right'>Unitario</th><th style='padding:10px;text-align:right'>Subtotal</th></tr></thead><tbody>{detail_rows}</tbody></table>
<div style='margin-top:20px;padding-top:16px;border-top:1px solid #d9e2ec;text-align:right;font-size:19px;font-weight:700'>Total: {_currency(order.total)}</div>
<p style='margin:24px 0 0;color:#667085;font-size:12px'>Se adjunta el comprobante PDF con el detalle del pedido.</p></div></div></body></html>""",
        subtype="html",
    )
    message.add_attachment(_order_pdf(order), maintype="application", subtype="pdf", filename=f"pedido-{order_code}.pdf")
    return message


def notify_administrators_via_whatsapp(
    database: Session, order: Pedido, pdf_bytes: bytes | None = None, tipo: str = "NUEVO_PEDIDO"
) -> None:
    """Envía la notificación del pedido y PDF por WhatsApp a los administradores con recibe_pedido=True y registra logs."""
    t_start = time.perf_counter()
    try:
        from app.services.whatsapp_service import WhatsAppService

        ws_service = WhatsAppService()

        # Validar conexión de WhatsApp
        is_connected = ws_service.is_connected_sync()
        if not is_connected:
            dur_ms = int((time.perf_counter() - t_start) * 1000)
            logger.info("Notificación WhatsApp omitida: La instancia '%s' no está vinculada o conectada.", ws_service.instance_name)
            _create_notification_log(
                database=database,
                pedido_id=order.id,
                canal="WHATSAPP",
                tipo=tipo,
                destinatario="Administradores",
                estado="OMITIDO",
                mensaje=f"Instancia de WhatsApp '{ws_service.instance_name}' no está conectada o vinculada.",
                duracion_ms=dur_ms,
            )
            return

        admin_users = list(
            database.scalars(
                select(Usuario).where(
                    Usuario.activo.is_(True),
                    Usuario.recibe_pedido.is_(True),
                )
            )
        )
        if not admin_users:
            dur_ms = int((time.perf_counter() - t_start) * 1000)
            logger.info("No hay usuarios activos con recibe_pedido=True configurados en el sistema.")
            _create_notification_log(
                database=database,
                pedido_id=order.id,
                canal="WHATSAPP",
                tipo=tipo,
                destinatario="Administradores",
                estado="OMITIDO",
                mensaje="No hay usuarios administradores activos con 'Recibe pedidos' habilitado.",
                duracion_ms=dur_ms,
            )
            return

        order_code = str(order.id).split("-")[0].upper()
        customer_name = order.cliente.nombre or order.cliente.rut or order.cliente.celular or "Cliente"
        customer_id = order.cliente.rut or order.cliente.celular or "Sin identificador"
        customer_phone = order.cliente.celular or "Sin teléfono"
        address = ", ".join(part for part in (order.direccion.direccion, order.direccion.comuna) if part) or "Sin dirección registrada"

        def _format_wa_item(d: object) -> str:
            tipo = getattr(d, "tipo_empaque", "unidad")
            cc = getattr(d, "cantidad_caja", None)
            emp = f" [Caja x{cc}]" if tipo == "caja" and cc else (" [Caja]" if tipo == "caja" else "")
            cant_txt = f"{d.cantidad} cj." if tipo == "caja" else f"{d.cantidad} un."
            return f"• {cant_txt} {d.nombre_producto}{emp} ({_currency(d.subtotal)})"

        items_lines = [
            _format_wa_item(d)
            for d in order.detalles[:8]
        ]
        if len(order.detalles) > 8:
            items_lines.append(f"• ... y {len(order.detalles) - 8} producto(s) más")
        items_summary = "\n".join(items_lines)


        caption = (
            f"🔔 *NUEVO PEDIDO REGISTRADO*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📋 *Pedido:* #{order_code}\n"
            f"👤 *Cliente:* {customer_name}\n"
            f"🆔 *RUT/ID:* {customer_id}\n"
            f"📞 *Teléfono:* {customer_phone}\n"
            f"📍 *Despacho:* {address}\n"
            f"💰 *Total:* {_currency(order.total)}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📦 *Detalle:*\n{items_summary}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📄 _Se adjunta comprobante en PDF con el detalle oficial._"
        )

        if pdf_bytes is None:
            pdf_bytes = _order_pdf(order)

        filename = f"pedido-{order_code}.pdf"

        for admin in admin_users:
            admin_start = time.perf_counter()
            phone = (admin.celular or "").strip()
            dest_label = f"{admin.nombre} ({phone})" if phone else admin.nombre
            if not phone:
                dur_ms = int((time.perf_counter() - admin_start) * 1000)
                logger.warning("El usuario '%s' tiene 'Recibe pedidos' pero no tiene número celular.", admin.nombre)
                _create_notification_log(
                    database=database,
                    pedido_id=order.id,
                    canal="WHATSAPP",
                    tipo=tipo,
                    destinatario=dest_label,
                    estado="OMITIDO",
                    mensaje="El usuario administrador no tiene número celular registrado.",
                    duracion_ms=dur_ms,
                )
                continue

            try:
                logger.info("Enviando notificación WhatsApp de pedido #%s a %s (%s)...", order_code, admin.nombre, phone)
                result = ws_service.send_pdf_document_sync(
                    phone=phone,
                    pdf_bytes=pdf_bytes,
                    filename=filename,
                    caption=caption,
                )
                dur_ms = int((time.perf_counter() - admin_start) * 1000)
                status_code = result.get("status") if isinstance(result, dict) else "OK"
                is_error = status_code == "ERROR" or (isinstance(status_code, int) and status_code >= 400)
                if is_error:
                    _create_notification_log(
                        database=database,
                        pedido_id=order.id,
                        canal="WHATSAPP",
                        tipo=tipo,
                        destinatario=dest_label,
                        estado="FALLIDO",
                        mensaje=f"Error en respuesta de API WhatsApp: {result.get('message', result)}",
                        error=str(result),
                        duracion_ms=dur_ms,
                    )
                else:
                    _create_notification_log(
                        database=database,
                        pedido_id=order.id,
                        canal="WHATSAPP",
                        tipo=tipo,
                        destinatario=dest_label,
                        estado="ENVIADO",
                        mensaje=f"Mensaje y comprobante PDF enviados correctamente a WhatsApp ({phone}).",
                        duracion_ms=dur_ms,
                    )
                logger.info("Notificación WhatsApp de pedido #%s enviada a %s (%s): %s", order_code, admin.nombre, phone, result)
            except Exception as e:
                dur_ms = int((time.perf_counter() - admin_start) * 1000)
                logger.exception("Error al enviar WhatsApp a %s (%s): %s", admin.nombre, phone, e)
                _create_notification_log(
                    database=database,
                    pedido_id=order.id,
                    canal="WHATSAPP",
                    tipo=tipo,
                    destinatario=dest_label,
                    estado="FALLIDO",
                    mensaje=f"Excepción al enviar WhatsApp a {phone}: {str(e)}",
                    error=traceback.format_exc(),
                    duracion_ms=dur_ms,
                )
    except Exception as e:
        dur_ms = int((time.perf_counter() - t_start) * 1000)
        logger.exception("Error general al procesar notificaciones WhatsApp para el pedido %s: %s", order.id, e)
        _create_notification_log(
            database=database,
            pedido_id=order.id,
            canal="WHATSAPP",
            tipo=tipo,
            destinatario="Sistema WhatsApp",
            estado="FALLIDO",
            mensaje=f"Fallo general en proceso WhatsApp: {str(e)}",
            error=traceback.format_exc(),
            duracion_ms=dur_ms,
        )


def notify_administrators_of_order(
    database: Session, order: Pedido, tipo: str = "NUEVO_PEDIDO"
) -> None:
    """Envía notificaciones de WhatsApp y Correo para un pedido y registra todos los logs."""
    # 1. Notificación vía WhatsApp con PDF adjunto
    pdf_bytes = _order_pdf(order)
    notify_administrators_via_whatsapp(database, order, pdf_bytes, tipo=tipo)

    # 2. Notificación vía Correo Electrónico (SMTP)
    smtp_start = time.perf_counter()
    smtp_config = _get_smtp_settings(database)
    if not smtp_config["configured"]:
        dur_ms = int((time.perf_counter() - smtp_start) * 1000)
        logger.warning("Pedido %s creado sin notificación de correo: SMTP no está configurado", order.id)
        _create_notification_log(
            database=database,
            pedido_id=order.id,
            canal="EMAIL_ADMIN",
            tipo=tipo,
            destinatario="Administradores",
            estado="OMITIDO",
            mensaje="Servidor SMTP no está configurado en el sistema.",
            duracion_ms=dur_ms,
        )
        return

    admin_recipients = [
        correo.strip()
        for correo in database.scalars(
            select(Usuario.correo)
            .where(Usuario.activo.is_(True), Usuario.recibe_pedido.is_(True))
        )
        if correo and correo.strip()
    ]
    customer_email = (order.cliente.correo or "").strip()

    # Envío a administradores
    if admin_recipients:
        admin_mail_start = time.perf_counter()
        admin_dest = ", ".join(admin_recipients)
        try:
            admin_msg = _build_order_message(
                order,
                admin_dest,
                f"Nuevo pedido #{str(order.id).split('-')[0].upper()} | Distribuidora Tridente",
                "NUEVO PEDIDO",
                "Se registró un nuevo pedido y requiere revisión.",
                True,
                from_name=smtp_config["from_name"],
                from_email=smtp_config["from_email"],
            )
            with smtplib.SMTP_SSL(smtp_config["host"], smtp_config["port"], timeout=20) as smtp:
                smtp.login(smtp_config["username"], smtp_config["password"])
                smtp.send_message(admin_msg)
            dur_ms = int((time.perf_counter() - admin_mail_start) * 1000)
            _create_notification_log(
                database=database,
                pedido_id=order.id,
                canal="EMAIL_ADMIN",
                tipo=tipo,
                destinatario=admin_dest,
                estado="ENVIADO",
                mensaje=f"Correo de nuevo pedido enviado exitosamente a {len(admin_recipients)} administrador(es).",
                duracion_ms=dur_ms,
            )
        except Exception as e:
            dur_ms = int((time.perf_counter() - admin_mail_start) * 1000)
            logger.exception("Error al enviar correo a administradores para el pedido %s", order.id)
            _create_notification_log(
                database=database,
                pedido_id=order.id,
                canal="EMAIL_ADMIN",
                tipo=tipo,
                destinatario=admin_dest,
                estado="FALLIDO",
                mensaje=f"Fallo al enviar correo a administradores: {str(e)}",
                error=traceback.format_exc(),
                duracion_ms=dur_ms,
            )
    else:
        _create_notification_log(
            database=database,
            pedido_id=order.id,
            canal="EMAIL_ADMIN",
            tipo=tipo,
            destinatario="Administradores",
            estado="OMITIDO",
            mensaje="No hay correos de administradores activos configurados para recibir pedidos.",
            duracion_ms=0,
        )

    # Envío al cliente
    if customer_email:
        cust_mail_start = time.perf_counter()
        try:
            cust_msg = _build_order_message(
                order,
                customer_email,
                f"Confirmación de pedido #{str(order.id).split('-')[0].upper()} | Distribuidora Tridente",
                "PEDIDO CONFIRMADO",
                "Recibimos tu pedido. Te avisaremos cuando su estado cambie.",
                False,
                from_name=smtp_config["from_name"],
                from_email=smtp_config["from_email"],
            )
            with smtplib.SMTP_SSL(smtp_config["host"], smtp_config["port"], timeout=20) as smtp:
                smtp.login(smtp_config["username"], smtp_config["password"])
                smtp.send_message(cust_msg)
            dur_ms = int((time.perf_counter() - cust_mail_start) * 1000)
            _create_notification_log(
                database=database,
                pedido_id=order.id,
                canal="EMAIL_CLIENTE",
                tipo=tipo,
                destinatario=customer_email,
                estado="ENVIADO",
                mensaje=f"Correo de confirmación de pedido enviado al cliente ({customer_email}).",
                duracion_ms=dur_ms,
            )
        except Exception as e:
            dur_ms = int((time.perf_counter() - cust_mail_start) * 1000)
            logger.exception("Error al enviar correo al cliente %s para el pedido %s", customer_email, order.id)
            _create_notification_log(
                database=database,
                pedido_id=order.id,
                canal="EMAIL_CLIENTE",
                tipo=tipo,
                destinatario=customer_email,
                estado="FALLIDO",
                mensaje=f"Fallo al enviar correo al cliente: {str(e)}",
                error=traceback.format_exc(),
                duracion_ms=dur_ms,
            )
    else:
        cust_name = order.cliente.nombre or "Cliente"
        _create_notification_log(
            database=database,
            pedido_id=order.id,
            canal="EMAIL_CLIENTE",
            tipo=tipo,
            destinatario=cust_name,
            estado="OMITIDO",
            mensaje="El cliente no tiene correo electrónico registrado.",
            duracion_ms=0,
        )


def _background_notification_runner(order_id: UUID, tipo: str = "NUEVO_PEDIDO") -> None:
    """Función ejecutada en hilo independiente para no bloquear la respuesta HTTP."""
    try:
        from app.core.database import SessionLocal

        from app.models.entities import DetallePedido

        with SessionLocal() as session:
            order = session.scalar(
                select(Pedido)
                .options(
                    selectinload(Pedido.detalles).selectinload(DetallePedido.producto),
                    selectinload(Pedido.estado),
                    selectinload(Pedido.cliente),
                    selectinload(Pedido.direccion),
                )
                .where(Pedido.id == order_id)
            )
            if not order:
                logger.error("No se encontró el pedido %s para notificaciones en segundo plano.", order_id)
                return

            notify_administrators_of_order(session, order, tipo=tipo)
    except Exception as e:
        logger.exception("Excepción no controlada en background_notification_runner para pedido %s: %s", order_id, e)


def dispatch_order_notifications_in_background(order_id: UUID, tipo: str = "NUEVO_PEDIDO") -> None:
    """Despacha las notificaciones en un hilo daemon en segundo plano para respuesta ultra rápida."""
    thread = threading.Thread(
        target=_background_notification_runner,
        args=(order_id, tipo),
        daemon=True,
    )
    thread.start()