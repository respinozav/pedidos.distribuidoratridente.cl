import React, { useState, useEffect, useRef } from "react";
import Swal from "sweetalert2";
import {
  Mail,
  MessageCircle,
  Save,
  CheckCircle2,
  Server,
  Send,
  QrCode,
  RefreshCw,
  AlertCircle,
  Smartphone,
} from "lucide-react";
import {
  getSettings,
  updateSettings,
  getWhatsAppStatus,
  getWhatsAppQR,
} from "../../services/settingsService";

function WhatsAppConnector() {
  const [status, setStatus] = useState("LOADING"); // LOADING, CONNECTED, DISCONNECTED, QR_READY, ERROR_API_DOWN
  const [qrBase64, setQrBase64] = useState(null);
  const [loadingAction, setLoadingAction] = useState(false);
  const pollIntervalRef = useRef(null);

  useEffect(() => {
    checkStatus();
    return () => {
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
    };
  }, []);

  const checkStatus = async () => {
    try {
      const data = await getWhatsAppStatus();
      const state = data?.instance?.state || data?.state || "DISCONNECTED";
      if (state === "open" || state === "CONNECTED" || state === "connecting") {
        setStatus(state === "open" ? "CONNECTED" : state);
        if (state === "open" || state === "CONNECTED") {
          setQrBase64(null);
          if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
        }
      } else if (state === "ERROR_API_DOWN") {
        setStatus("ERROR_API_DOWN");
      } else {
        setStatus("DISCONNECTED");
      }
    } catch {
      setStatus("DISCONNECTED");
    }
  };

  const handleGenerateQR = async () => {
    setLoadingAction(true);
    try {
      const data = await getWhatsAppQR();
      if (data.qr_code) {
        setQrBase64(data.qr_code.startsWith("data:") ? data.qr_code : `data:image/png;base64,${data.qr_code}`);
        setStatus("QR_READY");

        // Polling cada 4 segundos para detectar cuando el usuario escanee el QR
        if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = setInterval(async () => {
          try {
            const checkData = await getWhatsAppStatus();
            const state = checkData?.instance?.state || checkData?.state;
            if (state === "open" || state === "CONNECTED") {
              setStatus("CONNECTED");
              setQrBase64(null);
              clearInterval(pollIntervalRef.current);
              Swal.fire({
                icon: "success",
                title: "¡WhatsApp Vinculado!",
                text: "El dispositivo se conectó exitosamente.",
                timer: 2500,
                showConfirmButton: false,
              });
            }
          } catch {
            // Ignorar errores transitorios de polling
          }
        }, 4000);
      } else if (data.state === "CONNECTED" || data.state === "open") {
        setStatus("CONNECTED");
        setQrBase64(null);
      } else {
        await checkStatus();
      }
    } catch (err) {
      const detail = err.response?.data?.detail || "No se pudo generar el código QR. Verifica que el contenedor de Evolution API esté activo.";
      Swal.fire("Error", detail, "error");
    } finally {
      setLoadingAction(false);
    }
  };

  if (status === "LOADING") {
    return (
      <div className="py-5 text-center">
        <div className="spinner-border text-primary" role="status">
          <span className="visually-hidden">Cargando...</span>
        </div>
        <p className="text-muted mt-2 mb-0" style={{ fontSize: "0.85rem" }}>
          Consultando estado de WhatsApp...
        </p>
      </div>
    );
  }

  if (status === "open" || status === "CONNECTED") {
    return (
      <div className="text-center py-4">
        <div
          className="d-inline-flex flex-column align-items-center p-4 rounded-3"
          style={{ background: "#eaf8ef", border: "1px solid #c3edd2", maxWidth: "520px", width: "100%" }}
        >
          <CheckCircle2 size={44} className="text-success mb-2" />
          <h4 className="fw-bold text-success mb-1" style={{ fontSize: "1.1rem" }}>
            WhatsApp Conectado Correctamente
          </h4>
          <p className="text-secondary mb-3" style={{ fontSize: "0.85rem" }}>
            La instancia está activa y vinculada. El sistema puede enviar notificaciones automáticas a los clientes.
          </p>
          <button
            type="button"
            className="btn btn-outline-success btn-sm d-inline-flex align-items-center gap-2"
            onClick={checkStatus}
          >
            <RefreshCw size={15} />
            <span>Verificar estado de conexión</span>
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="text-center py-3">
      {status === "ERROR_API_DOWN" && (
        <div className="alert alert-warning d-inline-flex align-items-start gap-2 text-start mb-4" style={{ maxWidth: "600px" }}>
          <AlertCircle size={20} className="text-warning flex-shrink-0 mt-1" />
          <div style={{ fontSize: "0.84rem" }}>
            <strong>Microservicio Evolution API no disponible</strong>
            <p className="mb-0 mt-1">
              Asegúrate de ejecutar <code>docker compose up -d</code> en el servidor para iniciar el contenedor de WhatsApp en el puerto 8080.
            </p>
          </div>
        </div>
      )}

      <div className="mb-4" style={{ maxWidth: "540px", margin: "0 auto" }}>
        <div className="d-flex align-items-center justify-content-center gap-2 mb-2 text-primary">
          <Smartphone size={22} />
          <span className="fw-bold" style={{ fontSize: "0.95rem" }}>Vinculación de Dispositivo</span>
        </div>
        <p className="text-muted" style={{ fontSize: "0.84rem", lineHeight: 1.5 }}>
          Escanea el código QR con el celular de la empresa (<strong>WhatsApp Business</strong> &gt; <strong>Dispositivos Vinculados</strong> &gt; <strong>Vincular un dispositivo</strong>) para habilitar las notificaciones.
        </p>
      </div>

      {status === "QR_READY" && qrBase64 ? (
        <div className="d-inline-block p-4 bg-white border rounded-3 shadow-sm mb-3">
          <div className="position-relative d-inline-block">
            <img
              src={qrBase64}
              alt="Código QR de WhatsApp"
              className="rounded"
              style={{ width: "240px", height: "240px", objectFit: "contain", display: "block" }}
            />
          </div>
          <div className="mt-3">
            <div className="d-flex align-items-center justify-content-center gap-2 text-primary mb-3">
              <span className="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
              <small className="fw-semibold" style={{ fontSize: "0.78rem" }}>
                Esperando escaneo desde el móvil...
              </small>
            </div>
            <div className="d-flex justify-content-center gap-2">
              <button
                type="button"
                className="btn btn-outline-primary btn-sm d-inline-flex align-items-center gap-1"
                onClick={checkStatus}
              >
                <RefreshCw size={14} />
                <span>Verificar Conexión</span>
              </button>
              <button
                type="button"
                className="btn btn-outline-secondary btn-sm d-inline-flex align-items-center gap-1"
                onClick={handleGenerateQR}
                disabled={loadingAction}
              >
                <QrCode size={14} />
                <span>Regenerar QR</span>
              </button>
            </div>
          </div>
        </div>
      ) : (
        <div>
          <button
            type="button"
            className="btn btn-success d-inline-flex align-items-center gap-2 px-4 py-2"
            onClick={handleGenerateQR}
            disabled={loadingAction}
            style={{ fontWeight: 600, fontSize: "0.9rem" }}
          >
            {loadingAction ? (
              <>
                <span className="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
                <span>Generando código QR...</span>
              </>
            ) : (
              <>
                <QrCode size={18} />
                <span>Generar Código QR</span>
              </>
            )}
          </button>
        </div>
      )}
    </div>
  );
}

export default function SystemSettings() {
  const [activeTab, setActiveTab] = useState("smtp");
  const [loading, setLoading] = useState(false);
  const [fetching, setFetching] = useState(true);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [settings, setSettings] = useState({
    smtp_host: "",
    smtp_port: "",
    smtp_username: "",
    smtp_password: "",
    smtp_from_email: "",
    smtp_from_name: "",
    whatsapp_enabled: false,
    whatsapp_api_key: "",
    whatsapp_phone_number: "",
  });

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    setFetching(true);
    try {
      const data = await getSettings();
      setSettings((prev) => ({
        ...prev,
        ...data,
        smtp_port: data.smtp_port ? String(data.smtp_port) : "",
      }));
    } catch {
      setError("No fue posible cargar los ajustes del sistema.");
      Swal.fire("Error", "No fue posible cargar los ajustes del sistema.", "error");
    } finally {
      setFetching(false);
    }
  };

  const handleInputChange = (e) => {
    const { name, value, type, checked } = e.target;
    setSettings((prev) => ({
      ...prev,
      [name]: type === "checkbox" ? checked : value,
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setNotice("");
    setError("");
    try {
      const payload = {
        ...settings,
        smtp_port: settings.smtp_port ? parseInt(settings.smtp_port, 10) : null,
      };
      await updateSettings(payload);
      setNotice("Ajustes actualizados correctamente.");
      Swal.fire({
        icon: "success",
        title: "Ajustes guardados",
        text: "La configuración se ha actualizado correctamente.",
        timer: 2000,
        showConfirmButton: false,
      });
    } catch {
      setError("Ocurrió un error al guardar los ajustes.");
      Swal.fire("Error", "Ocurrió un error al guardar los ajustes.", "error");
    } finally {
      setLoading(false);
    }
  };

  const isSmtpConfigured = Boolean(
    settings.smtp_host &&
    settings.smtp_username &&
    settings.smtp_password &&
    settings.smtp_from_email
  );

  return (
    <>
      <header className="admin-topbar">
        <div className="topbar-title">
          <p className="eyebrow mb-1">CONFIGURACION</p>
          <h1>Ajustes del Sistema</h1>
        </div>
        <div className="topbar-actions">
          <span className="topbar-date d-none d-sm-inline">Parámetros globales</span>
        </div>
      </header>

      <div className="admin-content">
        <section className="admin-summary">
          <div>
            <p className="eyebrow">PARAMETROS</p>
            <h2>Configuración del Sistema</h2>
            <p>Gestiona las credenciales de correo SMTP y canales de comunicación.</p>
          </div>
          <div className="summary-metric">
            <span className="fs-4 fw-bold">{isSmtpConfigured ? "Activo" : "Pendiente"}</span>
            <small>Estado Correo (SMTP)</small>
          </div>
        </section>

        <section className="content-panel">
          <div className="panel-heading mb-3">
            <div>
              <h2>Servicios de Comunicación</h2>
              <p>Configura los servidores y parámetros para las notificaciones de pedidos.</p>
            </div>
            <span className="panel-count">{activeTab === "smtp" ? "SMTP" : "WhatsApp"}</span>
          </div>

          <div className="settings-tab-bar">
            <button
              type="button"
              className={`settings-tab-btn ${activeTab === "smtp" ? "active" : ""}`}
              onClick={() => setActiveTab("smtp")}
            >
              <Mail size={17} />
              <span>Correo (SMTP)</span>
            </button>
            <button
              type="button"
              className={`settings-tab-btn ${activeTab === "whatsapp" ? "active" : ""}`}
              onClick={() => setActiveTab("whatsapp")}
            >
              <MessageCircle size={17} />
              <span>WhatsApp (QR)</span>
            </button>
          </div>

          {notice && (
            <div className="alert alert-success alert-dismissible fade show mb-4 category-notice" role="alert">
              <CheckCircle2 size={18} />
              <span>{notice}</span>
              <button type="button" className="btn-close" aria-label="Cerrar" onClick={() => setNotice("")} />
            </div>
          )}

          {error && <div className="alert alert-danger mb-4">{error}</div>}

          {fetching ? (
            <p className="text-secondary py-3">Cargando ajustes...</p>
          ) : (
            <div>
              {activeTab === "smtp" && (
                <form onSubmit={handleSubmit}>
                  <div className="settings-card">
                    <div className="settings-card-header">
                      <div>
                        <h3>Servidor y Autenticación SMTP</h3>
                        <p>Datos de conexión con tu proveedor de correo.</p>
                      </div>
                      <Server size={18} className="text-muted" />
                    </div>
                    <div className="settings-card-body">
                      <div className="settings-field-group">
                        <div className="settings-field">
                          <label htmlFor="smtp_host">Servidor SMTP (Host)</label>
                          <input
                            id="smtp_host"
                            type="text"
                            className="form-control"
                            name="smtp_host"
                            value={settings.smtp_host || ""}
                            onChange={handleInputChange}
                            placeholder="ej. s560.v2nets.com o smtp.gmail.com"
                          />
                        </div>
                        <div className="settings-field">
                          <label htmlFor="smtp_port">Puerto SMTP</label>
                          <input
                            id="smtp_port"
                            type="number"
                            className="form-control"
                            name="smtp_port"
                            value={settings.smtp_port || ""}
                            onChange={handleInputChange}
                            placeholder="465 (SSL) o 587 (TLS)"
                          />
                        </div>
                        <div className="settings-field">
                          <label htmlFor="smtp_username">Usuario / Correo SMTP</label>
                          <input
                            id="smtp_username"
                            type="text"
                            className="form-control"
                            name="smtp_username"
                            value={settings.smtp_username || ""}
                            onChange={handleInputChange}
                            placeholder="pedidos@correotridente.cl"
                          />
                        </div>
                        <div className="settings-field">
                          <label htmlFor="smtp_password">Contraseña SMTP</label>
                          <input
                            id="smtp_password"
                            type="password"
                            className="form-control"
                            name="smtp_password"
                            value={settings.smtp_password || ""}
                            onChange={handleInputChange}
                            placeholder="••••••••••••"
                          />
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="settings-card">
                    <div className="settings-card-header">
                      <div>
                        <h3>Identidad del Remitente</h3>
                        <p>Nombre y dirección que verán los clientes al recibir los correos.</p>
                      </div>
                      <Send size={18} className="text-muted" />
                    </div>
                    <div className="settings-card-body">
                      <div className="settings-field-group">
                        <div className="settings-field">
                          <label htmlFor="smtp_from_email">Correo Remitente (From Email)</label>
                          <input
                            id="smtp_from_email"
                            type="email"
                            className="form-control"
                            name="smtp_from_email"
                            value={settings.smtp_from_email || ""}
                            onChange={handleInputChange}
                            placeholder="pedidos@correotridente.cl"
                          />
                        </div>
                        <div className="settings-field">
                          <label htmlFor="smtp_from_name">Nombre Remitente (From Name)</label>
                          <input
                            id="smtp_from_name"
                            type="text"
                            className="form-control"
                            name="smtp_from_name"
                            value={settings.smtp_from_name || ""}
                            onChange={handleInputChange}
                            placeholder="Distribuidora Tridente"
                          />
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="d-flex justify-content-end mt-4 pt-2">
                    <button type="submit" className="btn btn-primary" disabled={loading}>
                      {loading ? (
                        <>
                          <span className="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
                          <span>Guardando...</span>
                        </>
                      ) : (
                        <>
                          <Save size={17} />
                          <span>Guardar ajustes</span>
                        </>
                      )}
                    </button>
                  </div>
                </form>
              )}

              {activeTab === "whatsapp" && (
                <div className="settings-card">
                  <div className="settings-card-header">
                    <div>
                      <h3>Conexión de WhatsApp (Evolution API)</h3>
                      <p>Vincula el número oficial mediante código QR para notificaciones instantáneas.</p>
                    </div>
                    <MessageCircle size={18} className="text-success" />
                  </div>
                  <div className="settings-card-body">
                    <WhatsAppConnector />
                  </div>
                </div>
              )}
            </div>
          )}
        </section>
      </div>
    </>
  );
}
