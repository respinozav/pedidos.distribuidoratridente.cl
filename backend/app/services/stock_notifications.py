"""Servicio para gestión y despacho de avisos de reposición de stock a clientes."""

import html
import logging
import smtplib
from datetime import datetime, timezone
from email.message import EmailMessage
from email.utils import make_msgid
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.entities import AvisoStockCliente, Cliente, LogCorreo, Producto
from app.services.notifications import _get_smtp_settings

logger = logging.getLogger(__name__)


def _build_stock_replenished_html(
    cliente_nombre: str,
    producto_nombre: str,
    producto_codigo: str,
    stock_disponible: int,
    precio: float | None = None,
    portal_url: str = "https://pedidos.distribuidoratridente.cl",
) -> tuple[str, str, str]:
    """Genera el asunto, texto plano y HTML del correo de aviso de stock disponible."""
    asunto = f"¡Ya hay stock! {producto_nombre} disponible en Distribuidora Tridente"
    
    precio_str = f"${precio:,.0f}".replace(",", ".") if precio is not None else ""
    precio_html = f"""
      <tr>
        <td style="padding: 6px 0; color: #64748b; font-size: 14px;">Precio unitario:</td>
        <td style="padding: 6px 0; font-weight: 700; color: #0f172a; text-align: right; font-size: 15px;">{precio_str}</td>
      </tr>
    """ if precio_str else ""

    cuerpo_texto = (
        f"Hola {cliente_nombre},\n\n"
        f"¡Buenas noticias! Te avisamos que el producto que estabas esperando ya cuenta con stock disponible:\n\n"
        f"• Producto: {producto_nombre}\n"
        f"• Código: {producto_codigo}\n"
        f"• Stock disponible: {stock_disponible} unidades\n"
        + (f"• Precio: {precio_str}\n" if precio_str else "")
        + f"\nPuedes ingresar ahora mismo y agregarlo a tu pedido en:\n{portal_url}\n\n"
        f"Saludos cordiales,\nEquipo Distribuidora Tridente"
    )

    cuerpo_html = f"""<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
  <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <meta name="color-scheme" content="light" />
  <title>{html.escape(asunto)}</title>
</head>
<body style="margin:0;padding:0;background-color:#f1f5f9;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;color:#1e293b;">
  <table border="0" cellpadding="0" cellspacing="0" width="100%" style="background-color:#f1f5f9;table-layout:fixed;">
    <tr>
      <td align="center" style="padding:32px 12px;">
        <table border="0" cellpadding="0" cellspacing="0" width="100%" style="max-width:600px;background-color:#ffffff;border:1px solid #cbd5e1;border-top:6px solid #146cce;border-radius:12px;overflow:hidden;box-shadow:0 4px 6px -1px rgba(0,0,0,0.07);">
          
          <!-- Encabezado con Logo -->
          <tr>
            <td style="padding:28px 32px 20px 32px;border-bottom:1px solid #e2e8f0;background-color:#ffffff;">
              <table border="0" cellpadding="0" cellspacing="0" width="100%">
                <tr>
                  <td width="52" style="vertical-align:middle;padding-right:16px;">
                    <img src="https://pedidos.distribuidoratridente.cl/logo_tridente.png" alt="Logo Tridente" width="46" height="46" style="display:block;border:0;outline:none;" />
                  </td>
                  <td style="vertical-align:middle;">
                    <div style="font-size:22px;font-weight:800;color:#0f172a;letter-spacing:-0.5px;line-height:1.2;">Distribuidora Tridente</div>
                    <div style="color:#64748b;font-size:13px;font-weight:600;margin-top:4px;">Notificaciones de Catálogo y Stock</div>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Contenido principal -->
          <tr>
            <td style="padding:32px;">
              
              <!-- Badge de estado -->
              <div style="margin-bottom:18px;">
                <span style="display:inline-block;padding:6px 14px;background-color:#dbeafe;color:#1d4ed8;font-size:12px;font-weight:700;border-radius:20px;text-transform:uppercase;letter-spacing:0.5px;">
                  ✓ Reposición de Stock
                </span>
              </div>

              <!-- Saludo -->
              <h2 style="margin:0 0 14px 0;font-size:20px;font-weight:700;color:#0f172a;">
                ¡El producto que esperabas ya está disponible!
              </h2>

              <p style="margin:0 0 24px 0;font-size:15px;line-height:1.6;color:#334155;">
                Hola <strong>{html.escape(cliente_nombre)}</strong>,<br/>
                Te avisamos que el producto que consultaste recientemente ya cuenta con unidades disponibles en nuestra distribuidora.
              </p>

              <!-- Tarjeta de Producto -->
              <table border="0" cellpadding="0" cellspacing="0" width="100%" style="background-color:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;margin-bottom:28px;">
                <tr>
                  <td style="padding:20px;">
                    <div style="font-size:18px;font-weight:700;color:#0f172a;margin-bottom:6px;">
                      {html.escape(producto_nombre)}
                    </div>
                    <div style="font-size:13px;color:#64748b;margin-bottom:16px;">
                      Código SKU: <span style="font-family:monospace;font-weight:600;color:#334155;">{html.escape(producto_codigo)}</span>
                    </div>

                    <table border="0" cellpadding="0" cellspacing="0" width="100%" style="border-top:1px solid #e2e8f0;padding-top:12px;">
                      <tr>
                        <td style="padding:6px 0;color:#64748b;font-size:14px;">Stock disponible:</td>
                        <td style="padding:6px 0;font-weight:700;color:#16a34a;text-align:right;font-size:15px;">{stock_disponible} unidades</td>
                      </tr>
                      {precio_html}
                    </table>
                  </td>
                </tr>
              </table>

              <!-- Botón de acción principal -->
              <div style="text-align:center;margin-bottom:28px;">
                <a href="{portal_url}" style="display:inline-block;padding:14px 32px;background-color:#146cce;color:#ffffff;text-decoration:none;font-weight:700;font-size:15px;border-radius:8px;box-shadow:0 2px 4px rgba(20,108,206,0.3);">
                  Hacer Pedido Ahora →
                </a>
              </div>

              <!-- Recuadro informativo -->
              <table border="0" cellpadding="0" cellspacing="0" width="100%" style="background-color:#eff6ff;border:1px solid #bfdbfe;border-radius:8px;">
                <tr>
                  <td style="padding:14px 16px;font-size:13px;color:#1e40af;line-height:1.5;">
                    💡 <strong>Aprovecha antes de que se agote:</strong> El stock se actualiza en tiempo real según los pedidos recibidos por orden de llegada.
                  </td>
                </tr>
              </table>

            </td>
          </tr>

          <!-- Pie de página -->
          <tr>
            <td style="padding:20px 32px;background-color:#f8fafc;border-top:1px solid #e2e8f0;text-align:center;font-size:12px;color:#94a3b8;">
              Distribuidora Tridente · Recibiste este aviso porque solicitaste ser notificado cuando hubiera stock disponible.
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""

    return asunto, cuerpo_texto, cuerpo_html


def _despachar_email_aviso(
    smtp_config: dict,
    destinatario: str,
    asunto: str,
    cuerpo_texto: str,
    cuerpo_html: str,
) -> bool:
    """Envía el correo de aviso de stock usando el servidor SMTP configurado."""
    if not smtp_config.get("configured") or not smtp_config.get("host"):
        logger.warning("SMTP no configurado al intentar enviar aviso de stock a %s", destinatario)
        return False

    from_name = smtp_config.get("from_name") or "Distribuidora Tridente"
    from_email = smtp_config.get("from_email") or smtp_config.get("username")
    host = smtp_config.get("host")
    port = int(smtp_config.get("port") or 465)
    username = smtp_config.get("username")
    password = smtp_config.get("password")

    msg = EmailMessage()
    msg["Subject"] = asunto
    msg["From"] = f"{from_name} <{from_email}>"
    msg["To"] = destinatario
    msg["Message-ID"] = make_msgid(domain="distribuidoratridente.cl")
    msg["X-Entity-Ref-ID"] = make_msgid(domain="distribuidoratridente.cl")
    msg.set_content(cuerpo_texto)
    msg.add_alternative(cuerpo_html, subtype="html")

    if port == 465:
        with smtplib.SMTP_SSL(host, port, timeout=15) as smtp:
            smtp.login(username, password)
            smtp.send_message(msg)
    else:
        with smtplib.SMTP(host, port, timeout=15) as smtp:
            smtp.ehlo()
            smtp.login(username, password)
            smtp.send_message(msg)

    return True


def registrar_aviso_stock(
    database: Session,
    cliente_id: UUID,
    producto_id: UUID,
    correo: str,
) -> AvisoStockCliente:
    """Registra o actualiza la solicitud de aviso de reposición de stock de un cliente."""
    clean_correo = correo.strip().lower()
    
    # Buscar si ya existe una solicitud de este cliente para este producto
    aviso = database.scalar(
        select(AvisoStockCliente).where(
            AvisoStockCliente.cliente_id == cliente_id,
            AvisoStockCliente.producto_id == producto_id,
        )
    )

    if aviso:
        aviso.correo = clean_correo
        aviso.estado = "PENDIENTE"
        aviso.notificado_at = None
        aviso.updated_at = datetime.now(timezone.utc)
    else:
        aviso = AvisoStockCliente(
            cliente_id=cliente_id,
            producto_id=producto_id,
            correo=clean_correo,
            estado="PENDIENTE",
        )
        database.add(aviso)

    database.commit()
    database.refresh(aviso)
    logger.info("Aviso de stock registrado para cliente %s, producto %s, correo %s", cliente_id, producto_id, clean_correo)
    return aviso


def obtener_avisos_pendientes_cliente(database: Session, cliente_id: UUID) -> list[UUID]:
    """Retorna los IDs de productos para los cuales el cliente tiene un aviso pendiente activo."""
    return list(
        database.scalars(
            select(AvisoStockCliente.producto_id).where(
                AvisoStockCliente.cliente_id == cliente_id,
                AvisoStockCliente.estado == "PENDIENTE",
            )
        ).all()
    )


def procesar_avisos_stock_disponible(
    database: Session,
    producto_id: UUID | None = None,
) -> int:
    """
    Evalúa las solicitudes pendientes de aviso de stock.
    Condición de activación requerida: Producto.cantidad > 1 (más de 1 en stock).
    Despacha el correo de notificación y marca la solicitud como 'NOTIFICADO'.
    Retorna la cantidad de avisos notificados con éxito.
    """
    stmt = (
        select(AvisoStockCliente)
        .options(
            selectinload(AvisoStockCliente.producto),
            selectinload(AvisoStockCliente.cliente),
        )
        .join(Producto, AvisoStockCliente.producto_id == Producto.id)
        .where(
            AvisoStockCliente.estado == "PENDIENTE",
            Producto.activo.is_(True),
            Producto.eliminado_at.is_(None),
            Producto.cantidad > 1,  # Estrictamente mayor a 1 en stock según requerimiento
        )
    )

    if producto_id:
        stmt = stmt.where(AvisoStockCliente.producto_id == producto_id)

    avisos_a_procesar = list(database.scalars(stmt).all())
    if not avisos_a_procesar:
        return 0

    smtp_config = _get_smtp_settings(database)
    enviados_count = 0

    for aviso in avisos_a_procesar:
        producto = aviso.producto
        cliente = aviso.cliente
        if not producto or not cliente:
            continue

        cliente_nombre = cliente.nombre or cliente.rut or "Estimado/a Cliente"
        asunto, cuerpo_texto, cuerpo_html = _build_stock_replenished_html(
            cliente_nombre=cliente_nombre,
            producto_nombre=producto.nombre,
            producto_codigo=producto.codigo,
            stock_disponible=producto.cantidad,
            precio=float(producto.precio) if producto.precio is not None else None,
        )

        try:
            exito = _despachar_email_aviso(
                smtp_config=smtp_config,
                destinatario=aviso.correo,
                asunto=asunto,
                cuerpo_texto=cuerpo_texto,
                cuerpo_html=cuerpo_html,
            )

            # Se actualiza el aviso a NOTIFICADO
            aviso.estado = "NOTIFICADO"
            aviso.notificado_at = datetime.now(timezone.utc)
            aviso.updated_at = datetime.now(timezone.utc)

            # Registrar en log_correos
            log_entry = LogCorreo(
                cliente_id=aviso.cliente_id,
                destinatario=aviso.correo,
                tipo="AVISO_STOCK",
                asunto=asunto,
                cuerpo_enviado=cuerpo_texto,
                estado="ENVIADO" if exito else "ERROR_SMTP",
            )
            database.add(log_entry)
            database.commit()
            enviados_count += 1
            logger.info("Aviso de reposición de stock enviado exitosamente a %s para producto %s", aviso.correo, producto.nombre)

        except Exception as e:
            logger.exception("Error al enviar aviso de stock a %s: %s", aviso.correo, e)
            try:
                database.rollback()
            except Exception:
                pass

    return enviados_count
