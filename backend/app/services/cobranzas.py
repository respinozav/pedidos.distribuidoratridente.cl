"""
Servicio para renderizar y enviar correos de cobranza con diseño profesional y robusto compatible con Gmail (incluyendo modo oscuro y prevención de hilos/recortes).
"""

import html
import logging
import smtplib
import time
from datetime import datetime
from email.message import EmailMessage
from email.utils import make_msgid
from zoneinfo import ZoneInfo
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models.entities import Cliente, Credito, ConfiguracionAvisos, LogCorreo
from app.services.notifications import _get_smtp_settings

logger = logging.getLogger(__name__)

CHILE_TZ = ZoneInfo("America/Santiago")


def _render_template_vars(template: str, vars_dict: dict[str, str]) -> str:
    result = template
    for key, val in vars_dict.items():
        result = result.replace(f"{{{{{key}}}}}", str(val))
    return result


def _build_cobranza_html(
    titulo: str,
    asunto: str,
    cuerpo_texto: str,
    tipo: str,
) -> str:
    is_recordatorio = tipo == "RECORDATORIO"
    is_aviso = tipo == "AVISO_HOY" or tipo == "AVISO"

    top_bar_color = "#16a34a" if is_recordatorio else ("#d97706" if is_aviso else "#dc2626")
    badge_bg = "#dcfce7" if is_recordatorio else ("#fef08a" if is_aviso else "#fee2e2")
    badge_text = "#166534" if is_recordatorio else ("#854d0e" if is_aviso else "#991b1b")
    badge_border = "#86efac" if is_recordatorio else ("#eab308" if is_aviso else "#f87171")
    badge_label = (
        "⏰ RECORDATORIO PREVENTIVO DE CRÉDITO"
        if is_recordatorio
        else ("⚠️ AVISO DE VENCIMIENTO DE CRÉDITO (HOY)" if is_aviso else "🚨 CRÉDITO VENCIDO / EN MORA")
    )
    body_box_bg = "#f0fdf4" if is_recordatorio else ("#fffbeb" if is_aviso else "#fef2f2")
    body_box_border = "#bbf7d0" if is_recordatorio else ("#fde68a" if is_aviso else "#fecaca")
    body_box_left_border = "#16a34a" if is_recordatorio else ("#d97706" if is_aviso else "#dc2626")
    body_text_color = "#14532d" if is_recordatorio else ("#78350f" if is_aviso else "#7f1d1d")
    header_title = (
        "Recordatorio Preventivo de Pago"
        if is_recordatorio
        else ("Aviso de Vencimiento de Crédito" if is_aviso else "Cobranza de Crédito Vencido / En Mora")
    )

    cuerpo_html = html.escape(cuerpo_texto).replace("\n", "<br/>")

    return f"""<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
  <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <meta name="color-scheme" content="light" />
  <meta name="supported-color-schemes" content="light" />
  <title>{html.escape(asunto)}</title>
</head>
<body style="margin:0;padding:0;background-color:#f1f5f9;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;-webkit-text-size-adjust:none;color:#1e293b;">
  <table border="0" cellpadding="0" cellspacing="0" width="100%" style="background-color:#f1f5f9;table-layout:fixed;">
    <tr>
      <td align="center" style="padding:28px 12px;">
        <!-- Contenedor blanco principal 100% en tabla estándar para clientes de correo -->
        <table border="0" cellpadding="0" cellspacing="0" width="100%" style="max-width:600px;background-color:#ffffff;border:1px solid #cbd5e1;border-top:6px solid {top_bar_color};border-radius:12px;overflow:hidden;box-shadow:0 4px 6px -1px rgba(0,0,0,0.07);">
          
          <!-- FILA 1: Encabezado con Logo y Datos de Tridente dentro del contenedor blanco -->
          <tr>
            <td style="padding:28px 32px 20px 32px;border-bottom:1px solid #e2e8f0;background-color:#ffffff;">
              <table border="0" cellpadding="0" cellspacing="0" width="100%">
                <tr>
                  <td width="52" style="vertical-align:middle;padding-right:16px;">
                    <img src="https://pedidos.distribuidoratridente.cl/logo_tridente.png" alt="Logo Tridente" width="46" height="46" style="display:block;border:0;outline:none;" />
                  </td>
                  <td style="vertical-align:middle;">
                    <div style="font-size:22px;font-weight:800;color:#0f172a;letter-spacing:-0.5px;line-height:1.2;">Distribuidora Tridente</div>
                    <div style="color:#64748b;font-size:13px;font-weight:600;margin-top:4px;">Departamento de Finanzas y Cobranzas</div>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- FILA 2: Contenido principal -->
          <tr>
            <td style="padding:28px 32px;background-color:#ffffff;">
              <!-- Badge Alerta -->
              <table border="0" cellpadding="0" cellspacing="0" style="margin-bottom:18px;">
                <tr>
                  <td style="background-color:{badge_bg};border:1.5px solid {badge_border};border-radius:24px;padding:6px 14px;color:{badge_text};font-size:12px;font-weight:800;letter-spacing:0.04em;">
                    {badge_label}
                  </td>
                </tr>
              </table>

              <!-- Titulo -->
              <div style="font-size:19px;font-weight:700;color:#0f172a;margin-bottom:16px;">
                {header_title}
              </div>

              <!-- Recuadro Destacado con el texto -->
              <table border="0" cellpadding="0" cellspacing="0" width="100%" style="background-color:{body_box_bg};border:2px solid {body_box_border};border-left:8px solid {body_box_left_border};border-radius:8px;margin-bottom:24px;">
                <tr>
                  <td style="padding:20px 24px;font-size:15px;line-height:1.7;color:{body_text_color};font-weight:500;">
                    {cuerpo_html}
                  </td>
                </tr>
              </table>

              <!-- Recuadro información comprobante -->
              <table border="0" cellpadding="0" cellspacing="0" width="100%" style="background-color:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;">
                <tr>
                  <td style="padding:16px;font-size:13px;color:#475569;line-height:1.5;">
                    <strong style="color:#0f172a;">Información importante:</strong> Si ya realizó su transferencia o pago, por favor remita el comprobante respondiendo a este correo para actualizar su estado de cuenta.
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- FILA 3: Pie de página -->
          <tr>
            <td style="padding:18px 28px;background-color:#f8fafc;border-top:1px solid #e2e8f0;text-align:center;font-size:12px;color:#94a3b8;">
              Distribuidora Tridente · Mensaje generado automáticamente por el sistema de cobranzas
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def _enviar_email_smtp(
    smtp_config: dict,
    destinatario: str,
    asunto: str,
    cuerpo_texto: str,
    cuerpo_html: str,
) -> bool:
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


def procesar_avisos_cobranza_smtp(database: Session) -> dict:
    """
    Evalúa créditos y envía recordatorios, avisos del día y vencimientos por SMTP.
    Usa la zona horaria America/Santiago para determinar la fecha actual y de vencimiento.
    Evita envíos duplicados el mismo día.
    """
    config = database.scalar(select(ConfiguracionAvisos).filter(ConfiguracionAvisos.id == 1))
    if not config or not config.activo:
        return {
            "status": "skipped",
            "mensaje": "El servicio de avisos automáticos está deshabilitado.",
            "recordatorios_enviados": 0,
            "avisos_hoy_enviados": 0,
            "vencidos_mora_enviados": 0,
        }

    smtp_config = _get_smtp_settings(database)
    if not smtp_config.get("configured"):
        logger.error("No se pudo ejecutar el job de cobranza: SMTP no configurado.")
        return {
            "status": "error",
            "mensaje": "Servidor SMTP no configurado en los ajustes del sistema.",
            "recordatorios_enviados": 0,
            "avisos_hoy_enviados": 0,
            "vencidos_mora_enviados": 0,
        }

    ahora_santiago = datetime.now(CHILE_TZ)
    hoy_santiago = ahora_santiago.date()

    statement = (
        select(Credito, Cliente)
        .join(Cliente, Cliente.id == Credito.cliente_id)
        .filter(
            Credito.pagado == False,
            Cliente.activo == True,
            Cliente.correo.isnot(None),
            Cliente.correo != "",
        )
    )
    rows = list(database.execute(statement).all())

    enviados_recordatorio = 0
    enviados_aviso = 0
    enviados_vencido = 0
    errores = []

    for credito, cliente in rows:
        destinatario = cliente.correo.strip()
        if not destinatario:
            continue

        fecha_venc_dt = credito.fecha_vencimiento
        if fecha_venc_dt.tzinfo is None:
            fecha_venc_dt = fecha_venc_dt.replace(tzinfo=ZoneInfo("UTC"))
        fecha_venc_santiago = fecha_venc_dt.astimezone(CHILE_TZ).date()

        diff_dias = (fecha_venc_santiago - hoy_santiago).days
        fecha_venc_str = fecha_venc_santiago.strftime("%d/%m/%Y")

        tipo_envio = None
        dias_mora = 0

        if diff_dias == 1:
            tipo_envio = "RECORDATORIO"
        elif diff_dias == 0:
            tipo_envio = "AVISO_HOY"
        elif diff_dias < 0:
            tipo_envio = "VENCIDO"
            dias_mora = abs(diff_dias)

        if not tipo_envio:
            continue

        log_existente = database.scalar(
            select(LogCorreo.id).filter(
                LogCorreo.credito_id == credito.id,
                LogCorreo.tipo == tipo_envio,
                text("DATE(enviado_el AT TIME ZONE 'America/Santiago') = :hoy").params(hoy=hoy_santiago),
            )
        )
        if log_existente:
            continue

        vars_dict = {
            "nombre": cliente.nombre or "Cliente",
            "dias_credito": str(credito.dias_credito or 0),
            "fecha_vencimiento": fecha_venc_str,
            "dias_mora": str(dias_mora),
        }

        if tipo_envio == "RECORDATORIO":
            asunto = _render_template_vars(config.asunto_recordatorio, vars_dict)
            cuerpo_texto = _render_template_vars(config.plantilla_recordatorio, vars_dict)
        elif tipo_envio == "AVISO_HOY":
            asunto = _render_template_vars(config.asunto_aviso, vars_dict)
            cuerpo_texto = _render_template_vars(config.plantilla_aviso, vars_dict)
        else:
            asunto = _render_template_vars(config.asunto_vencido or "Urgente: Tu crédito se encuentra VENCIDO", vars_dict)
            cuerpo_texto = _render_template_vars(
                config.plantilla_vencido
                or "Estimado/a {{nombre}}, le informamos que su crédito por {{dias_credito}} días se encuentra VENCIDO desde el {{fecha_vencimiento}} ({{dias_mora}} días de mora). Favor regularizar su saldo a la brevedad.",
                vars_dict,
            )

        html_content = _build_cobranza_html(
            titulo=asunto,
            asunto=asunto,
            cuerpo_texto=cuerpo_texto,
            tipo=tipo_envio,
        )

        try:
            _enviar_email_smtp(
                smtp_config=smtp_config,
                destinatario=destinatario,
                asunto=asunto,
                cuerpo_texto=cuerpo_texto,
                cuerpo_html=html_content,
            )

            log_entry = LogCorreo(
                credito_id=credito.id,
                cliente_id=cliente.id,
                destinatario=destinatario,
                tipo=tipo_envio,
                asunto=asunto,
                cuerpo_enviado=cuerpo_texto,
                estado="ENVIADO",
            )
            database.add(log_entry)
            database.commit()

            if tipo_envio == "RECORDATORIO":
                enviados_recordatorio += 1
            elif tipo_envio == "AVISO_HOY":
                enviados_aviso += 1
            else:
                enviados_vencido += 1

            logger.info("Aviso de cobranza [%s] enviado exitosamente a %s", tipo_envio, destinatario)
        except Exception as e:
            logger.exception("Error enviando aviso [%s] a %s: %s", tipo_envio, destinatario, e)
            errores.append(f"{destinatario} ({tipo_envio}): {str(e)}")
            try:
                database.rollback()
            except Exception:
                pass

    return {
        "status": "success" if not errores else "partial",
        "recordatorios_enviados": enviados_recordatorio,
        "avisos_hoy_enviados": enviados_aviso,
        "vencidos_mora_enviados": enviados_vencido,
        "errores": errores,
        "ejecutado_el": ahora_santiago.isoformat(),
    }
