import html
import logging
import re
import smtplib
import time
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from email.message import EmailMessage
from io import BytesIO
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from pydantic import BaseModel, Field
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.entities import CotizacionCliente, CotizacionProducto

from app.core.config import get_settings
from app.services.notifications import _currency, _get_smtp_settings, _get_system_timezone
from app.services.whatsapp_service import WhatsAppService, format_whatsapp_phone

logger = logging.getLogger(__name__)

LOGO_PATH = Path(__file__).resolve().parents[2] / "assets" / "logo_tridente.png"


# ==============================================================================
# ESQUEMAS DE DATOS PARA COTIZACIONES
# ==============================================================================

class CotizacionItemInput(BaseModel):
    producto_id: str | None = None
    codigo_producto: str = ""
    nombre_producto: str
    precio_unitario: Decimal = Field(default=Decimal(0), ge=0)
    cantidad: int = Field(default=1, ge=1)
    subtotal: Decimal = Field(default=Decimal(0), ge=0)
    afecto: bool = True
    tipo_empaque: str = "unidad"  # "unidad" o "caja"
    cantidad_caja: int | None = None


class CotizacionInput(BaseModel):
    codigo: str | None = None
    cliente_id: str | None = None
    cliente_nombre: str
    cliente_rut: str | None = None
    cliente_correo: str | None = None
    cliente_telefono: str | None = None
    cliente_direccion: str | None = None
    cliente_comuna: str | None = None
    validez_dias: int = Field(default=15, ge=1, le=90)
    observaciones: str | None = None
    items: list[CotizacionItemInput]


class CotizacionEmailInput(BaseModel):
    cotizacion: CotizacionInput
    destinatario_correo: str
    mensaje_adicional: str | None = None


class CotizacionWhatsAppInput(BaseModel):
    cotizacion: CotizacionInput
    destinatario_telefono: str
    mensaje_adicional: str | None = None


# ==============================================================================
# VALIDACIONES DE FORMATO
# ==============================================================================

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
PHONE_REGEX = re.compile(r"^(\+?56)?\s?9\d{8}$")


def validar_email(email: str) -> bool:
    """Valida formato de correo electrónico estricto."""
    if not email or not isinstance(email, str):
        return False
    return bool(EMAIL_REGEX.match(email.strip()))


def validar_telefono_cl(phone: str) -> bool:
    """Valida formato de teléfono móvil chileno (ej: +56912345678, 912345678, 56912345678)."""
    if not phone or not isinstance(phone, str):
        return False
    clean = re.sub(r"[\s\-\(\)]", "", phone.strip())
    return bool(PHONE_REGEX.match(clean))


# ==============================================================================
# GENERACIÓN DE PDF DE COTIZACIÓN (CLON EXACTO DE FORMATO DE PEDIDOS)
# ==============================================================================

def generar_cotizacion_pdf(
    cotizacion: CotizacionInput,
    database: Session | None = None,
) -> tuple[bytes, str]:
    """
    Genera un documento PDF idéntico en tipografía, colores, dimensiones y estructura
    al comprobante de pedidos de Distribuidora Tridente, pero con denominación de COTIZACIÓN.
    """
    quote_code = cotizacion.codigo or f"COT-{uuid.uuid4().hex[:6].upper()}"
    cotizacion.codigo = quote_code

    system_tz = _get_system_timezone(database)
    now_dt = datetime.now(system_tz)
    fecha_emision = now_dt.strftime("%d-%m-%Y %H:%M")
    fecha_vencimiento = (now_dt + timedelta(days=cotizacion.validez_dias)).strftime("%d-%m-%Y")

    customer_name = cotizacion.cliente_nombre.strip() or "Cliente"
    customer_id = (cotizacion.cliente_rut or "").strip() or "Sin identificador"
    customer_email = (cotizacion.cliente_correo or "").strip() or "Sin correo registrado"
    customer_phone = (cotizacion.cliente_telefono or "").strip() or "Sin teléfono registrado"
    
    address_parts = [p for p in (cotizacion.cliente_direccion, cotizacion.cliente_comuna) if p and p.strip()]
    address = ", ".join(address_parts) if address_parts else "A convenir / Sin dirección"

    output = BytesIO()
    document = SimpleDocTemplate(
        output,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="CotizadorBrand",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=20,
        textColor=colors.HexColor("#172B4D"),
        leading=24,
    ))
    styles.add(ParagraphStyle(
        name="CotizadorCode",
        parent=styles["Normal"],
        alignment=TA_RIGHT,
        fontName="Helvetica-Bold",
        fontSize=14,
        textColor=colors.HexColor("#172B4D"),
    ))
    styles.add(ParagraphStyle(
        name="CotizadorDetails",
        parent=styles["Normal"],
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#334E68"),
    ))
    styles.add(ParagraphStyle(
        name="CotizadorProductCell",
        parent=styles["Normal"],
        fontSize=9,
        leading=11,
        textColor=colors.HexColor("#334E68"),
    ))
    styles.add(ParagraphStyle(
        name="CotizadorFootnote",
        parent=styles["Normal"],
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#64748B"),
    ))

    story = []

    # 1. Cabecera con Logo y Código de Cotización
    brand = Image(str(LOGO_PATH), width=45 * mm, height=30 * mm, kind="proportional") if LOGO_PATH.is_file() else Paragraph("Distribuidora Tridente", styles["CotizadorBrand"])
    header = Table([[brand, Paragraph(f"COTIZACIÓN #{quote_code}", styles["CotizadorCode"])]], colWidths=[95 * mm, 79 * mm])
    header.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LINEBELOW", (0, 0), (-1, -1), 1.2, colors.HexColor("#146CCE")),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.extend([header, Spacer(1, 7 * mm)])

    # 2. Información del Cliente y de la Cotización
    customer_details = "<br/>".join((
        f"<b>Cliente / Razón Social:</b> {html.escape(customer_name)}",
        f"<b>RUT / Identificador:</b> {html.escape(customer_id)}",
        f"<b>Correo Electrónico:</b> {html.escape(customer_email)}",
        f"<b>Teléfono:</b> {html.escape(customer_phone)}",
        f"<b>Fecha de emisión:</b> {fecha_emision}",
        f"<b>Vigencia de la oferta:</b> {cotizacion.validez_dias} días (hasta el {fecha_vencimiento})",
        f"<b>Dirección / Entrega:</b> {html.escape(address)}",
    ))
    if cotizacion.observaciones and cotizacion.observaciones.strip():
        customer_details += f"<br/><b>Observaciones:</b> {html.escape(cotizacion.observaciones.strip())}"

    story.extend([Paragraph(customer_details, styles["CotizadorDetails"]), Spacer(1, 6 * mm)])

    # 3. Tabla de Productos (ordenada: afectos primero, exentos después, idéntico a pedidos)
    sorted_items = sorted(cotizacion.items, key=lambda d: 0 if d.afecto else 1)

    rows = [["Producto", "Cantidad", "IVA", "Precio Unit.", "Subtotal"]]
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

    total_acumulado = Decimal(0)
    total_unidades = 0
    total_cajas = 0

    for row_idx, item in enumerate(sorted_items, start=1):
        subtotal = item.subtotal if item.subtotal > 0 else (item.precio_unitario * item.cantidad)
        total_acumulado += subtotal

        iva_text = "Afecto" if item.afecto else "Exento"
        if item.afecto:
            table_styles.append(("BACKGROUND", (0, row_idx), (-1, row_idx), colors.HexColor("#F0F2F5")))

        name_escaped = html.escape(item.nombre_producto)
        code_escaped = html.escape(item.codigo_producto) if item.codigo_producto else ""
        emp_badge = f" <font color='#146CCE'><b>(Caja x{item.cantidad_caja})</b></font>" if item.tipo_empaque == "caja" and item.cantidad_caja else (" <font color='#146CCE'><b>(Caja)</b></font>" if item.tipo_empaque == "caja" else "")
        code_badge = f" <font color='#667085'>[{code_escaped}]</font>" if code_escaped else ""

        product_label = f"<b>{name_escaped}</b>{emp_badge}{code_badge}"
        product_para = Paragraph(product_label, styles["CotizadorProductCell"])

        cant_str = f"{item.cantidad} cj." if item.tipo_empaque == "caja" else f"{item.cantidad} un."
        if item.tipo_empaque == "caja":
            total_cajas += item.cantidad
        else:
            total_unidades += item.cantidad

        rows.append([
            product_para,
            cant_str,
            iva_text,
            _currency(item.precio_unitario),
            _currency(subtotal),
        ])

    details_table = Table(rows, colWidths=[74 * mm, 18 * mm, 22 * mm, 28 * mm, 32 * mm], repeatRows=1)
    details_table.setStyle(TableStyle(table_styles))
    story.append(details_table)

    # 4. Conteo de ítems y Totales
    total_items = len(sorted_items)
    items_label = f"Total productos: {total_items} ítem{'s' if total_items != 1 else ''}"
    cant_desglose = []
    if total_unidades:
        cant_desglose.append(f"{total_unidades} un.")
    if total_cajas:
        cant_desglose.append(f"{total_cajas} cj.")
    if cant_desglose:
        items_label += f" ({', '.join(cant_desglose)})"

    total_formatted = f"${total_acumulado:,.0f}.- Imp. Inc.".replace(",", ".")
    footer_rows = [
        [
            Paragraph(f"<font color='#667085'><b>{html.escape(items_label)}</b></font>", styles["CotizadorDetails"]),
            "TOTAL",
            total_formatted,
        ]
    ]

    total_table = Table(footer_rows, colWidths=[74 * mm, 30 * mm, 70 * mm], hAlign="RIGHT")
    total_table.setStyle(TableStyle([
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("FONTNAME", (1, 0), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (1, 0), (-1, -1), 11),
        ("ALIGN", (0, 0), (0, -1), "LEFT"),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("ALIGN", (2, 0), (2, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TEXTCOLOR", (1, 0), (-1, -1), colors.HexColor("#172B4D")),
    ]))
    story.extend([total_table, Spacer(1, 8 * mm)])

    # 5. Notas legales y comerciales
    notes_html = (
        "<b>Condiciones de la cotización:</b><br/>"
        f"• Valores expresados en pesos chilenos (CLP) con impuestos incluidos.<br/>"
        f"• Esta cotización no reserva stock de productos de forma inmediata.<br/>"
        f"• Válida hasta el <b>{fecha_vencimiento}</b> o hasta agotar existencias.<br/>"
        "• Para confirmar y procesar este pedido, comuníquese con su ejecutivo comercial o responda a este documento."
    )
    story.append(Paragraph(notes_html, styles["CotizadorFootnote"]))

    document.build(story)
    pdf_bytes = output.getvalue()

    safe_name = re.sub(r'[\\/*?:"<>|]', "", customer_name)
    safe_name = re.sub(r"\s+", " ", safe_name).strip()
    filename = f"Cotizacion - {safe_name} - {quote_code}.pdf" if safe_name else f"Cotizacion-{quote_code}.pdf"

    return pdf_bytes, filename


# ==============================================================================
# ENVÍO DE COTIZACIÓN POR CORREO ELECTRÓNICO
# ==============================================================================

def enviar_cotizacion_email(
    database: Session,
    input_data: CotizacionEmailInput,
    usuario_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    """Envía la cotización en PDF adjunta al correo electrónico del cliente."""
    clean_recipient = input_data.destinatario_correo.strip()
    if not validar_email(clean_recipient):
        raise HTTPException(status_code=400, detail="El formato del correo electrónico ingresado no es válido.")

    if not input_data.cotizacion.items:
        raise HTTPException(status_code=400, detail="La cotización debe contener al menos un producto.")

    pdf_bytes, filename = generar_cotizacion_pdf(input_data.cotizacion, database)

    smtp_config = _get_smtp_settings(database)
    if not smtp_config.get("configured") or not smtp_config.get("host"):
        raise HTTPException(
            status_code=400,
            detail="El servidor de correos no está configurado en el sistema. Revise los Ajustes del Sistema.",
        )

    quote_code = input_data.cotizacion.codigo or f"COT-{uuid.uuid4().hex[:6].upper()}"
    client_name = input_data.cotizacion.cliente_nombre.strip() or "Estimado/a Cliente"
    total_calc = sum(
        (item.subtotal if item.subtotal > 0 else (item.precio_unitario * item.cantidad))
        for item in input_data.cotizacion.items
    )

    from_name = smtp_config.get("from_name") or "Distribuidora Tridente"
    from_email = smtp_config.get("from_email") or smtp_config.get("username")
    host = smtp_config.get("host")
    port = int(smtp_config.get("port") or 465)
    username = smtp_config.get("username")
    password = smtp_config.get("password")

    msg = EmailMessage()
    msg["Subject"] = f"Cotización #{quote_code} | Distribuidora Tridente"
    msg["From"] = f"{from_name} <{from_email}>"
    msg["To"] = clean_recipient

    # Construir filas de la tabla HTML de productos
    detail_rows = []
    for item in input_data.cotizacion.items:
        bg = "background:#f0f2f5;" if item.afecto else ""
        tipo_emp = item.tipo_empaque
        cant_caja = item.cantidad_caja
        emp_badge = f" <span style='color:#146CCE;font-weight:600'>(Caja x{cant_caja})</span>" if tipo_emp == "caja" and cant_caja else (" <span style='color:#146CCE;font-weight:600'>(Caja)</span>" if tipo_emp == "caja" else "")
        cant_str = f"{item.cantidad} cj." if tipo_emp == "caja" else f"{item.cantidad} un."
        subtotal_item = item.subtotal if item.subtotal > 0 else (item.precio_unitario * item.cantidad)
        code_str = f" <span style='color:#667085;font-size:12px'>[{html.escape(item.codigo_producto)}]</span>" if item.codigo_producto else ""
        detail_rows.append(
            f"<tr style='{bg}'>"
            f"<td style='padding:8px 10px;border-top:1px solid #d9e2ec'><strong>{html.escape(item.nombre_producto)}</strong>{emp_badge}{code_str}</td>"
            f"<td style='padding:8px 10px;border-top:1px solid #d9e2ec;text-align:center'>{cant_str}</td>"
            f"<td style='padding:8px 10px;border-top:1px solid #d9e2ec;text-align:center'>{'Afecto' if item.afecto else 'Exento'}</td>"
            f"<td style='padding:8px 10px;border-top:1px solid #d9e2ec;text-align:right'>{_currency(item.precio_unitario)}</td>"
            f"<td style='padding:8px 10px;border-top:1px solid #d9e2ec;text-align:right'>{_currency(subtotal_item)}</td>"
            f"</tr>"
        )
    rows_html = "".join(detail_rows)

    mensaje_extra_html = ""
    if input_data.mensaje_adicional and input_data.mensaje_adicional.strip():
        mensaje_extra_html = (
            f"<div style='margin-bottom:18px;padding:12px 16px;background:#f8fafc;border-left:4px solid #146CCE;border-radius:4px;font-size:14px;color:#334E68;'>"
            f"<b>Nota de su ejecutivo:</b> {html.escape(input_data.mensaje_adicional.strip())}"
            f"</div>"
        )

    html_body = f"""<!DOCTYPE html>
<html>
<head><meta charset='utf-8'></head>
<body style='margin:0;padding:24px;background:#f4f6f8;font-family:Arial,Helvetica,sans-serif;color:#172B4D;'>
  <div style='max-width:680px;margin:0 auto;background:#ffffff;border-radius:12px;overflow:hidden;border:1px solid #d9e2ec;box-shadow:0 4px 6px -1px rgba(0,0,0,0.06);'>
    <div style='background:#102a43;padding:24px 32px;'>
      <table width='100%' border='0' cellspacing='0' cellpadding='0'>
        <tr>
          <td width='48' style='vertical-align:middle;padding-right:14px;'>
            <img src='https://pedidos.distribuidoratridente.cl/logo_tridente.png' alt='Logo Tridente' width='42' height='42' style='display:block;border:0;outline:none;' />
          </td>
          <td style='vertical-align:middle;'>
            <div style='font-size:22px;font-weight:700;color:#ffffff;line-height:1.2;'>Distribuidora Tridente</div>
            <div style='margin-top:4px;color:#9bceff;font-size:11px;font-weight:700;letter-spacing:1px;text-transform:uppercase;'>Cotización de Productos</div>
          </td>
          <td align='right' style='vertical-align:middle;'>
            <div style='font-size:18px;font-weight:700;color:#ffffff;'>Cotización #{quote_code}</div>
          </td>
        </tr>
      </table>
    </div>
    <div style='padding:28px 32px;'>
      <p style='font-size:15px;margin-top:0;'>Hola <strong>{html.escape(client_name)}</strong>,</p>
      <p style='color:#334e68;line-height:1.5;'>Agradecemos su interés en nuestros productos. A continuación le presentamos el resumen de su cotización formal:</p>
      {mensaje_extra_html}
      <table style='width:100%;border-collapse:collapse;margin-top:16px;'>
        <thead>
          <tr style='background:#f8fafc;color:#667085;font-size:12px;text-align:left;'>
            <th style='padding:10px;'>Producto</th>
            <th style='padding:10px;text-align:center;'>Cant.</th>
            <th style='padding:10px;text-align:center;'>IVA</th>
            <th style='padding:10px;text-align:right;'>Unitario</th>
            <th style='padding:10px;text-align:right;'>Subtotal</th>
          </tr>
        </thead>
        <tbody>{rows_html}</tbody>
      </table>
      <div style='margin-top:20px;padding-top:16px;border-top:1px solid #d9e2ec;text-align:right;font-size:20px;font-weight:700;color:#172B4D;'>
        Total Cotizado: {_currency(total_calc)}
      </div>
      <p style='margin:24px 0 0;color:#667085;font-size:12px;'>
        📎 <strong>Se adjunta el comprobante formal en PDF</strong> con el detalle completo y las condiciones comerciales.<br/>
        Válida por {input_data.cotizacion.validez_dias} días a partir de su emisión.
      </p>
    </div>
  </div>
</body>
</html>"""

    plain_body = (
        f"Hola {client_name},\n\n"
        f"Adjuntamos su cotización formal #{quote_code} emitida por Distribuidora Tridente.\n"
        f"Total Cotizado: {_currency(total_calc)}\n"
        f"Validez: {input_data.cotizacion.validez_dias} días.\n\n"
        f"Atentamente,\nDistribuidora Tridente"
    )

    msg.set_content(plain_body)
    msg.add_alternative(html_body, subtype="html")
    msg.add_attachment(pdf_bytes, maintype="application", subtype="pdf", filename=filename)

    start_time = time.perf_counter()
    try:
        if port == 465:
            with smtplib.SMTP_SSL(host, port, timeout=18) as smtp:
                smtp.login(username, password)
                smtp.send_message(msg)
        else:
            with smtplib.SMTP(host, port, timeout=18) as smtp:
                smtp.ehlo()
                smtp.login(username, password)
                smtp.send_message(msg)
        dur_ms = int((time.perf_counter() - start_time) * 1000)
        logger.info("Cotización %s enviada por correo a %s en %sms", quote_code, clean_recipient, dur_ms)
        return {
            "success": True,
            "message": f"Cotización enviada exitosamente a {clean_recipient}",
            "filename": filename,
        }
    except Exception as ex:
        logger.error("Error al enviar cotización por correo a %s: %s", clean_recipient, ex, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"No fue posible enviar el correo: {str(ex)[:150]}",
        )


# ==============================================================================
# ENVÍO DE COTIZACIÓN POR WHATSAPP (DOCUMENTO PDF)
# ==============================================================================

def enviar_cotizacion_whatsapp(
    database: Session,
    input_data: CotizacionWhatsAppInput,
    usuario_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    """Envía el PDF de la cotización y el resumen a través de WhatsApp (Evolution API)."""
    raw_phone = input_data.destinatario_telefono.strip()
    if not validar_telefono_cl(raw_phone):
        raise HTTPException(
            status_code=400,
            detail="El número de WhatsApp ingresado no tiene un formato válido (ej: +56912345678 o 912345678).",
        )

    clean_phone = format_whatsapp_phone(raw_phone)
    if not clean_phone:
        raise HTTPException(status_code=400, detail="No se pudo formatear el número para WhatsApp.")

    if not input_data.cotizacion.items:
        raise HTTPException(status_code=400, detail="La cotización debe contener al menos un producto.")

    pdf_bytes, filename = generar_cotizacion_pdf(input_data.cotizacion, database)

    quote_code = input_data.cotizacion.codigo or f"COT-{uuid.uuid4().hex[:6].upper()}"
    client_name = input_data.cotizacion.cliente_nombre.strip() or "Estimado/a Cliente"
    total_calc = sum(
        (item.subtotal if item.subtotal > 0 else (item.precio_unitario * item.cantidad))
        for item in input_data.cotizacion.items
    )

    system_tz = _get_system_timezone(database)
    now_dt = datetime.now(system_tz)
    fecha_emision = now_dt.strftime("%d-%m-%Y")
    fecha_vencimiento = (now_dt + timedelta(days=input_data.cotizacion.validez_dias)).strftime("%d-%m-%Y")

    items_lines = []
    for item in input_data.cotizacion.items[:8]:
        tipo_emp = item.tipo_empaque
        cant_caja = item.cantidad_caja
        emp = f" [Caja x{cant_caja}]" if tipo_emp == "caja" and cant_caja else (" [Caja]" if tipo_emp == "caja" else "")
        cant_txt = f"{item.cantidad} cj." if tipo_emp == "caja" else f"{item.cantidad} un."
        sub_item = item.subtotal if item.subtotal > 0 else (item.precio_unitario * item.cantidad)
        items_lines.append(f"• {cant_txt} {item.nombre_producto}{emp} ({_currency(sub_item)})")
    
    if len(input_data.cotizacion.items) > 8:
        items_lines.append(f"• ... y {len(input_data.cotizacion.items) - 8} producto(s) más")
    items_summary = "\n".join(items_lines)

    nota_extra = ""
    if input_data.mensaje_adicional and input_data.mensaje_adicional.strip():
        nota_extra = f"\n💬 *Nota:* {input_data.mensaje_adicional.strip()}\n"

    caption = (
        f"📋 *COTIZACIÓN #{quote_code}*\n"
        f"🏢 *Distribuidora Tridente*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 *Cliente:* {client_name}\n"
        f"📅 *Fecha:* {fecha_emision}\n"
        f"⏱️ *Vigencia:* Hasta el {fecha_vencimiento} ({input_data.cotizacion.validez_dias} días)\n"
        f"💰 *Total Cotizado:* {_currency(total_calc)}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📦 *Detalle:*\n{items_summary}\n"
        f"━━━━━━━━━━━━━━━━━━━━{nota_extra}\n"
        f"📄 _Se adjunta documento oficial en PDF con las condiciones comerciales._"
    )

    ws_service = WhatsAppService()
    try:
        res = ws_service.send_pdf_document_sync(
            phone=clean_phone,
            pdf_bytes=pdf_bytes,
            filename=filename,
            caption=caption,
        )
        if isinstance(res, dict) and res.get("status") == "ERROR":
            raise HTTPException(
                status_code=502,
                detail=res.get("message") or "Error al enviar documento por WhatsApp.",
            )
        return {
            "success": True,
            "message": f"Cotización enviada exitosamente por WhatsApp a +{clean_phone}",
            "filename": filename,
        }
    except HTTPException:
        raise
    except Exception as ex:
        logger.error("Error al enviar WhatsApp a %s: %s", clean_phone, ex, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Fallo en la comunicación con WhatsApp: {str(ex)[:150]}",
        )


# ==============================================================================
# PERSISTENCIA Y CONSULTA DE HISTORIAL DE COTIZACIONES
# ==============================================================================

def guardar_cotizacion_en_bd(
    database: Session,
    cotizacion: CotizacionInput,
    usuario_id: uuid.UUID | None = None,
) -> CotizacionCliente:
    """
    Persiste la cotización y cada uno de sus productos en las tablas
    cotizaciones_clientes y cotizaciones_productos.
    """
    if not cotizacion.codigo:
        cotizacion.codigo = f"COT-{uuid.uuid4().hex[:6].upper()}"

    # Revisar si ya existe cotización con este folio para evitar duplicados
    existente = database.query(CotizacionCliente).filter(CotizacionCliente.folio == cotizacion.codigo).first()
    if existente:
        return existente

    # Calcular totales
    subtotal_neto = Decimal(0)
    subtotal_exento = Decimal(0)
    total_unidades = 0

    for item in cotizacion.items:
        cant = item.cantidad
        total_unidades += cant
        sub = item.subtotal if item.subtotal > 0 else (item.precio_unitario * cant)
        if item.afecto:
            subtotal_neto += sub
        else:
            subtotal_exento += sub

    iva = (subtotal_neto * Decimal("0.19")).quantize(Decimal("1"))
    total_final = subtotal_neto + subtotal_exento + iva
    total_items = len(cotizacion.items)

    system_tz = _get_system_timezone(database)
    now_dt = datetime.now(system_tz)
    fecha_vencimiento = now_dt + timedelta(days=cotizacion.validez_dias)

    productos_data = [
        {
            "id": item.producto_id,
            "codigo": item.codigo_producto or "S/C",
            "nombre": item.nombre_producto,
            "tipo_empaque": item.tipo_empaque or "unidad",
            "cantidad_caja": item.cantidad_caja,
            "precio_unitario": float(item.precio_unitario),
            "cantidad": item.cantidad,
            "subtotal": float(item.subtotal if item.subtotal > 0 else (item.precio_unitario * item.cantidad)),
            "afecto": bool(item.afecto),
        }
        for item in cotizacion.items
    ]

    cot_db = CotizacionCliente(
        folio=cotizacion.codigo,
        cliente_razon_social=cotizacion.cliente_nombre.strip() or "Cliente",
        cliente_rut=(cotizacion.cliente_rut or "").strip(),
        cliente_telefono=(cotizacion.cliente_telefono or "").strip(),
        cliente_correo=(cotizacion.cliente_correo or "").strip(),
        cliente_direccion=(cotizacion.cliente_direccion or "").strip() or "A convenir / Sin dirección",
        cliente_comuna=(cotizacion.cliente_comuna or "").strip(),
        cliente_observaciones=(cotizacion.observaciones or "").strip(),
        fecha_emision=now_dt,
        fecha_vencimiento=fecha_vencimiento,
        subtotal_neto=subtotal_neto,
        subtotal_exento=subtotal_exento,
        iva=iva,
        total=total_final,
        total_items=total_items,
        total_unidades=total_unidades,
        productos=productos_data,
        estado="emitida",
        usuario_id=usuario_id,
    )
    database.add(cot_db)
    database.flush()

    for item in cotizacion.items:
        sub_it = item.subtotal if item.subtotal > 0 else (item.precio_unitario * item.cantidad)
        prod_db = CotizacionProducto(
            cotizacion_id=cot_db.id,
            cotizacion_folio=cot_db.folio,
            cliente_rut=cot_db.cliente_rut,
            cliente_razon_social=cot_db.cliente_razon_social,
            producto_id=item.producto_id,
            codigo_sku=item.codigo_producto or "S/C",
            nombre_producto=item.nombre_producto,
            tipo_empaque=item.tipo_empaque or "unidad",
            cantidad_caja=item.cantidad_caja,
            precio_unitario=item.precio_unitario,
            cantidad=item.cantidad,
            subtotal=sub_it,
            afecto_iva=item.afecto,
            fecha_cotizacion=now_dt,
        )
        database.add(prod_db)

    database.commit()
    database.refresh(cot_db)
    return cot_db


def obtener_clientes_cotizantes(
    database: Session,
    query: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """
    Retorna clientes únicos que han cotizado previamente en el sitio web,
    agrupados por RUT (o identificador/nombre), con sus datos de contacto más recientes
    y la fecha de su última cotización.
    """
    clean_q = (query or "").strip().lower()
    db_query = database.query(CotizacionCliente)

    if clean_q:
        q_no_punct = re.sub(r"[^0-9kK]", "", clean_q).upper()
        if q_no_punct:
            pattern_rut = f"%{q_no_punct}%"
            pattern_text = f"%{clean_q}%"
            db_query = db_query.filter(
                (func.replace(func.replace(func.upper(CotizacionCliente.cliente_rut), ".", ""), "-", "").like(pattern_rut))
                | (CotizacionCliente.cliente_razon_social.ilike(pattern_text))
                | (CotizacionCliente.cliente_rut.ilike(pattern_text))
                | (CotizacionCliente.cliente_correo.ilike(pattern_text))
            )
        else:
            pattern_text = f"%{clean_q}%"
            db_query = db_query.filter(
                (CotizacionCliente.cliente_razon_social.ilike(pattern_text))
                | (CotizacionCliente.cliente_correo.ilike(pattern_text))
            )

    cotizaciones = (
        db_query.order_by(CotizacionCliente.fecha_emision.desc())
        .limit(500)
        .all()
    )

    clientes_map: dict[str, dict[str, Any]] = {}

    for cot in cotizaciones:
        rut_clean = re.sub(r"[^0-9kK]", "", cot.cliente_rut or "").upper()
        key = rut_clean if rut_clean else (cot.cliente_razon_social or "").strip().lower()
        if not key:
            continue

        if key not in clientes_map:
            clientes_map[key] = {
                "rut": cot.cliente_rut or "",
                "rut_clean": rut_clean,
                "nombre": cot.cliente_razon_social or "",
                "razon_social": cot.cliente_razon_social or "",
                "telefono": cot.cliente_telefono or "",
                "correo": cot.cliente_correo or "",
                "direccion": cot.cliente_direccion or "",
                "comuna": cot.cliente_comuna or "",
                "ultima_fecha": cot.fecha_emision.isoformat() if cot.fecha_emision else "",
                "ultimo_folio": cot.folio,
                "total_cotizaciones": 1,
            }
        else:
            clientes_map[key]["total_cotizaciones"] += 1
            if not clientes_map[key]["telefono"] and cot.cliente_telefono:
                clientes_map[key]["telefono"] = cot.cliente_telefono
            if not clientes_map[key]["correo"] and cot.cliente_correo:
                clientes_map[key]["correo"] = cot.cliente_correo
            if not clientes_map[key]["direccion"] and cot.cliente_direccion:
                clientes_map[key]["direccion"] = cot.cliente_direccion
            if not clientes_map[key]["comuna"] and cot.cliente_comuna:
                clientes_map[key]["comuna"] = cot.cliente_comuna

    result = list(clientes_map.values())
    return result[:limit]


def obtener_historial_cotizante(
    database: Session,
    identificador: str,
) -> list[dict[str, Any]]:
    """
    Retorna el historial completo de cotizaciones y sus productos detallados
    para un cliente cotizante dado su RUT o nombre.
    """
    ident_clean = identificador.strip()
    rut_digits = re.sub(r"[^0-9kK]", "", ident_clean).upper()

    query = database.query(CotizacionCliente)
    if rut_digits:
        pattern_rut = f"%{rut_digits}%"
        pattern_text = f"%{ident_clean}%"
        query = query.filter(
            (func.replace(func.replace(func.upper(CotizacionCliente.cliente_rut), ".", ""), "-", "").like(pattern_rut))
            | (CotizacionCliente.cliente_razon_social.ilike(pattern_text))
            | (CotizacionCliente.cliente_rut.ilike(pattern_text))
        )
    else:
        pattern_text = f"%{ident_clean}%"
        query = query.filter(
            (CotizacionCliente.cliente_razon_social.ilike(pattern_text))
            | (CotizacionCliente.cliente_rut.ilike(pattern_text))
        )

    cotizaciones = query.order_by(CotizacionCliente.fecha_emision.desc()).limit(50).all()

    historial = []
    for cot in cotizaciones:
        items = []
        for p in cot.items:
            items.append({
                "id": str(p.id),
                "producto_id": p.producto_id,
                "codigo_sku": p.codigo_sku or "S/C",
                "nombre_producto": p.nombre_producto,
                "tipo_empaque": p.tipo_empaque or "unidad",
                "cantidad_caja": p.cantidad_caja,
                "precio_unitario": float(p.precio_unitario),
                "cantidad": p.cantidad,
                "subtotal": float(p.subtotal),
                "afecto_iva": p.afecto_iva,
                "fecha_cotizacion": p.fecha_cotizacion.isoformat() if p.fecha_cotizacion else "",
            })

        if not items and cot.productos and isinstance(cot.productos, list):
            for p in cot.productos:
                p_unit = float(p.get("precio_unitario") or p.get("precio") or p.get("unit_price") or 0)
                p_cant = int(p.get("cantidad") or p.get("qty") or 1)
                p_sub = float(p.get("subtotal") or (p_unit * p_cant))
                items.append({
                    "id": str(p.get("id") or ""),
                    "producto_id": p.get("producto_id") or p.get("id"),
                    "codigo_sku": p.get("codigo_sku") or p.get("codigo") or p.get("sku") or "S/C",
                    "nombre_producto": p.get("nombre_producto") or p.get("nombre") or p.get("producto") or "Producto sin nombre",
                    "tipo_empaque": p.get("tipo_empaque") or "unidad",
                    "cantidad_caja": p.get("cantidad_caja"),
                    "precio_unitario": p_unit,
                    "cantidad": p_cant,
                    "subtotal": p_sub,
                    "afecto_iva": bool(p.get("afecto", p.get("afecto_iva", True))),
                    "fecha_cotizacion": cot.fecha_emision.isoformat() if cot.fecha_emision else "",
                })

        historial.append({
            "id": str(cot.id),
            "folio": cot.folio,
            "fecha_emision": cot.fecha_emision.isoformat() if cot.fecha_emision else "",
            "fecha_vencimiento": cot.fecha_vencimiento.isoformat() if cot.fecha_vencimiento else "",
            "cliente_razon_social": cot.cliente_razon_social,
            "cliente_rut": cot.cliente_rut,
            "cliente_telefono": cot.cliente_telefono,
            "cliente_correo": cot.cliente_correo,
            "cliente_direccion": cot.cliente_direccion,
            "cliente_comuna": cot.cliente_comuna or "",
            "cliente_observaciones": cot.cliente_observaciones or "",
            "subtotal_neto": float(cot.subtotal_neto or 0),
            "subtotal_exento": float(cot.subtotal_exento or 0),
            "iva": float(cot.iva or 0),
            "total": float(cot.total or 0),
            "total_items": cot.total_items or len(items),
            "total_unidades": cot.total_unidades or sum(it["cantidad"] for it in items),
            "estado": cot.estado or "emitida",
            "items": items,
        })

    return historial

