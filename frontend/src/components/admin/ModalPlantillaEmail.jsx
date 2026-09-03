import React, { useState, useEffect } from "react";
import { X, Tag, Save, Send } from "lucide-react";
import Swal from "sweetalert2";
import { sendTestEmail } from "../../services/settingsService";

export default function ModalPlantillaEmail({
  isOpen,
  onClose,
  tipo,
  titulo,
  asuntoInicial,
  cuerpoInicial,
  onGuardar,
  cargando,
}) {
  const [asunto, setAsunto] = useState("");
  const [cuerpo, setCuerpo] = useState("");
  const [probando, setProbando] = useState(false);

  useEffect(() => {
    if (isOpen) {
      setAsunto(asuntoInicial || "");
      setCuerpo(cuerpoInicial || "");
    }
  }, [isOpen, asuntoInicial, cuerpoInicial]);

  if (!isOpen) return null;

  const insertarVariable = (variable) => {
    setCuerpo((prev) => `${prev} {{${variable}}}`);
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    onGuardar({ asunto, cuerpo });
  };

  const handleProbarEnvio = async () => {
    if (!asunto.trim() || !cuerpo.trim()) {
      Swal.fire("Plantilla incompleta", "Ingresa un asunto y cuerpo para probar el envío.", "warning");
      return;
    }

    const { value: email } = await Swal.fire({
      title: "Probar Plantilla por Correo",
      text: "Ingresa el correo al que deseas enviar esta plantilla con datos de prueba:",
      input: "email",
      inputPlaceholder: "ejemplo@correo.com",
      showCancelButton: true,
      confirmButtonText: "Enviar Prueba",
      cancelButtonText: "Cancelar",
      confirmButtonColor: "#0284c7",
      cancelButtonColor: "#64748b",
      inputValidator: (val) => {
        if (!val || !val.trim()) {
          return "Por favor ingresa un correo electrónico.";
        }
        if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(val.trim())) {
          return "El formato del correo no es válido.";
        }
      },
    });

    if (!email) return;

    setProbando(true);
    Swal.fire({
      title: "Enviando prueba...",
      html: `Generando plantilla y despachando a <b>${email}</b>.`,
      allowOutsideClick: false,
      didOpen: () => {
        Swal.showLoading();
      },
    });

    try {
      const hoy = new Date();
      const fechaVenc = new Date(hoy.setDate(hoy.getDate() + 1)).toLocaleDateString("es-CL");

      const asuntoRenderizado = asunto
        .replaceAll("{{nombre}}", "Juan Pérez (Prueba)")
        .replaceAll("{{dias_credito}}", "30")
        .replaceAll("{{fecha_vencimiento}}", fechaVenc);

      const cuerpoRenderizado = cuerpo
        .replaceAll("{{nombre}}", "Juan Pérez")
        .replaceAll("{{dias_credito}}", "30")
        .replaceAll("{{dias_mora}}", "5")
        .replaceAll("{{fecha_vencimiento}}", fechaVenc);

      const isRecordatorio = tipo === "RECORDATORIO" || titulo?.toLowerCase().includes("recordatorio");
      const isAviso = tipo === "AVISO" || titulo?.toLowerCase().includes("aviso");
      const isVencido = tipo === "VENCIDO" || titulo?.toLowerCase().includes("vencido");
      
      const topBarColor = isRecordatorio ? "#16a34a" : isAviso ? "#d97706" : "#dc2626";
      const badgeBg = isRecordatorio ? "#dcfce7" : isAviso ? "#fef08a" : "#fee2e2";
      const badgeText = isRecordatorio ? "#166534" : isAviso ? "#854d0e" : "#991b1b";
      const badgeBorder = isRecordatorio ? "#86efac" : isAviso ? "#eab308" : "#f87171";
      const badgeLabel = isRecordatorio
        ? "⏰ RECORDATORIO PREVENTIVO DE CRÉDITO"
        : isAviso
        ? "⚠️ AVISO DE VENCIMIENTO DE CRÉDITO (HOY)"
        : "🚨 CRÉDITO VENCIDO / EN MORA";
      
      const bodyBoxBg = isRecordatorio ? "#f0fdf4" : isAviso ? "#fffbeb" : "#fef2f2";
      const bodyBoxBorder = isRecordatorio ? "#bbf7d0" : isAviso ? "#fde68a" : "#fecaca";
      const bodyBoxLeftBorder = isRecordatorio ? "#16a34a" : isAviso ? "#d97706" : "#dc2626";
      const bodyTextColor = isRecordatorio ? "#14532d" : isAviso ? "#78350f" : "#7f1d1d";
      const headerTitle = isRecordatorio
        ? "Recordatorio Preventivo de Pago"
        : isAviso
        ? "Aviso de Vencimiento de Crédito"
        : "Cobranza de Crédito Vencido / En Mora";

      const htmlBody = `<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
  <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <meta name="color-scheme" content="light" />
  <meta name="supported-color-schemes" content="light" />
  <title>${asuntoRenderizado}</title>
</head>
<body style="margin:0;padding:0;background-color:#f1f5f9;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;-webkit-text-size-adjust:none;color:#1e293b;">
  <table border="0" cellpadding="0" cellspacing="0" width="100%" style="background-color:#f1f5f9;table-layout:fixed;">
    <tr>
      <td align="center" style="padding:28px 12px;">
        <table border="0" cellpadding="0" cellspacing="0" width="100%" style="max-width:600px;background-color:#ffffff;border:1px solid #cbd5e1;border-top:6px solid ${topBarColor};border-radius:12px;overflow:hidden;box-shadow:0 4px 6px -1px rgba(0,0,0,0.07);">
          
          <!-- FILA 1: Encabezado dentro del contenedor blanco -->
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
              <!-- Badge de Alerta -->
              <table border="0" cellpadding="0" cellspacing="0" style="margin-bottom:18px;">
                <tr>
                  <td style="background-color:${badgeBg};border:1.5px solid ${badgeBorder};border-radius:24px;padding:6px 14px;color:${badgeText};font-size:12px;font-weight:800;letter-spacing:0.04em;">
                    ${badgeLabel}
                  </td>
                </tr>
              </table>

              <div style="font-size:19px;font-weight:700;color:#0f172a;margin-bottom:16px;">
                ${headerTitle}
              </div>
              
              <!-- Recuadro Destacado con el texto -->
              <table border="0" cellpadding="0" cellspacing="0" width="100%" style="background-color:${bodyBoxBg};border:2px solid ${bodyBoxBorder};border-left:8px solid ${bodyBoxLeftBorder};border-radius:8px;margin-bottom:24px;">
                <tr>
                  <td style="padding:20px 24px;font-size:15px;line-height:1.7;color:${bodyTextColor};font-weight:500;">
                    ${cuerpoRenderizado.replaceAll("\n", "<br/>")}
                  </td>
                </tr>
              </table>

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
</html>`;

      await sendTestEmail({
        recipient: email.trim(),
        subject: `[PRUEBA] ${asuntoRenderizado}`,
        body_text: cuerpoRenderizado,
        body_html: htmlBody,
      });

      Swal.fire({
        icon: "success",
        title: "¡Correo de prueba enviado!",
        html: `<p>Se envió la plantilla correctamente a <b>${email}</b>.</p><p class="text-muted small mb-0">Verifica cómo se ve en tu bandeja de entrada.</p>`,
        confirmButtonColor: "#16a34a",
      });
    } catch (err) {
      const errorMsg =
        err.response?.data?.detail ||
        err.message ||
        "No se pudo enviar la prueba de correo.";
      Swal.fire({
        icon: "error",
        title: "Error al enviar prueba",
        text: typeof errorMsg === "string" ? errorMsg : JSON.stringify(errorMsg),
      });
    } finally {
      setProbando(false);
    }
  };

  return (
    <div
      className="modal-backdrop-custom d-flex align-items-center justify-content-center"
      style={{
        position: "fixed",
        inset: 0,
        backgroundColor: "rgba(15, 23, 42, 0.75)",
        backdropFilter: "blur(4px)",
        zIndex: 1050,
        padding: "1rem",
      }}
    >
      <div
        className="card border-0 shadow-lg rounded-4 overflow-hidden w-100"
        style={{ maxWidth: "640px", backgroundColor: "#ffffff" }}
        role="dialog"
        aria-modal="true"
      >
        <div className="card-header bg-light border-bottom d-flex align-items-center justify-content-between px-4 py-3">
          <div>
            <h5 className="mb-0 fw-bold text-dark">{titulo}</h5>
            <small className="text-muted">
              Personaliza el asunto, cuerpo y utiliza tags dinámicos
            </small>
          </div>
          <button
            type="button"
            className="btn btn-sm btn-outline-secondary rounded-circle p-1 d-flex align-items-center justify-content-center"
            style={{ width: "32px", height: "32px" }}
            onClick={onClose}
            aria-label="Cerrar"
          >
            <X size={18} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-4">
          <div className="mb-3">
            <label className="form-label fw-bold small text-secondary text-uppercase mb-1">
              Asunto del Correo
            </label>
            <input
              type="text"
              className="form-control"
              value={asunto}
              onChange={(e) => setAsunto(e.target.value)}
              placeholder="Ej. Recordatorio de vencimiento de crédito"
              required
            />
          </div>

          <div className="mb-3">
            <div className="d-flex align-items-center justify-content-between mb-1">
              <label className="form-label fw-bold small text-secondary text-uppercase mb-0">
                Cuerpo del Correo
              </label>
              <div className="d-flex align-items-center gap-1">
                <small className="text-muted d-flex align-items-center gap-1 me-1">
                  <Tag size={12} /> Tags:
                </small>
                {["nombre", "dias_credito", "fecha_vencimiento", ...(tipo === "VENCIDO" ? ["dias_mora"] : [])].map((tag) => (
                  <button
                    key={tag}
                    type="button"
                    onClick={() => insertarVariable(tag)}
                    className="btn btn-sm btn-outline-primary py-0 px-2 rounded-pill font-monospace"
                    style={{ fontSize: "0.75rem" }}
                  >
                    {`{{${tag}}}`}
                  </button>
                ))}
              </div>
            </div>

            <textarea
              rows={6}
              className="form-control font-monospace"
              style={{ fontSize: "0.88rem" }}
              value={cuerpo}
              onChange={(e) => setCuerpo(e.target.value)}
              placeholder="Escribe el texto del correo..."
              required
            />
          </div>

          <div className="d-flex justify-content-between align-items-center gap-2 pt-3 border-top">
            <button
              type="button"
              className="btn btn-outline-secondary d-inline-flex align-items-center gap-2"
              onClick={handleProbarEnvio}
              disabled={cargando || probando}
            >
              <Send size={15} />
              <span>{probando ? "Enviando prueba..." : "Probar Envío"}</span>
            </button>
            <div className="d-flex gap-2">
              <button
                type="button"
                className="btn btn-light px-4"
                onClick={onClose}
                disabled={cargando || probando}
              >
                Cancelar
              </button>
              <button
                type="submit"
                className="btn btn-primary px-4 d-inline-flex align-items-center gap-2"
                disabled={cargando || probando}
              >
                {cargando ? (
                  <>
                    <span className="spinner-border spinner-border-sm" role="status" aria-hidden="true" />
                    <span>Guardando...</span>
                  </>
                ) : (
                  <>
                    <Save size={16} />
                    <span>Guardar Plantilla</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}

