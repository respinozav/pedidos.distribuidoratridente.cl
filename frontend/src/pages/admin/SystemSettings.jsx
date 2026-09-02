import React, { useState, useEffect, useRef } from "react";
import Swal from "sweetalert2";
import {
  Mail,
  MessageCircle,
  Clock,
  Save,
  CheckCircle2,
  Server,
  Send,
  QrCode,
  RefreshCw,
  AlertCircle,
  Smartphone,
  LogOut,
  Phone,
  Check,
  Bell,
} from "lucide-react";
import NotificacionesTab from "./NotificacionesTab";
import { api } from "../../services/api";
import {
  getSettings,
  updateSettings,
  getWhatsAppStatus,
  getWhatsAppQR,
  disconnectWhatsApp,
  sendTestEmail,
} from "../../services/settingsService";

function WhatsAppConnector({ onStatusUpdate }) {
  const [status, setStatus] = useState("LOADING"); // LOADING, CONNECTED, DISCONNECTED, QR_READY, ERROR_API_DOWN
  const [qrBase64, setQrBase64] = useState(null);
  const [instanceInfo, setInstanceInfo] = useState(null);
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
      const instance = data?.instance || {};
      const state = instance.state || data?.state || "DISCONNECTED";
      setInstanceInfo(instance);
      if (onStatusUpdate) onStatusUpdate(instance);

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
      if (onStatusUpdate) onStatusUpdate({ state: "DISCONNECTED" });
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
            const instance = checkData?.instance || {};
            const state = instance.state || checkData?.state;
            if (state === "open" || state === "CONNECTED") {
              setStatus("CONNECTED");
              setQrBase64(null);
              setInstanceInfo(instance);
              if (onStatusUpdate) onStatusUpdate(instance);
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
        await checkStatus();
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

  const handleDisconnect = async () => {
    const result = await Swal.fire({
      title: "¿Desvincular WhatsApp?",
      text: "El sistema dejará de enviar notificaciones por WhatsApp hasta que vuelvas a vincular un dispositivo escaneando el código QR.",
      icon: "warning",
      showCancelButton: true,
      confirmButtonColor: "#dc3545",
      cancelButtonColor: "#6c757d",
      confirmButtonText: "Sí, desvincular",
      cancelButtonText: "Cancelar",
    });

    if (result.isConfirmed) {
      setLoadingAction(true);
      try {
        await disconnectWhatsApp();
        setStatus("DISCONNECTED");
        setQrBase64(null);
        setInstanceInfo(null);
        if (onStatusUpdate) onStatusUpdate({ state: "DISCONNECTED" });
        Swal.fire({
          icon: "success",
          title: "Dispositivo Desvinculado",
          text: "La sesión de WhatsApp ha sido cerrada correctamente.",
          timer: 2000,
          showConfirmButton: false,
        });
      } catch (err) {
        Swal.fire("Error", "No fue posible desvincular el dispositivo.", "error");
      } finally {
        setLoadingAction(false);
      }
    }
  };

  if (status === "LOADING") {
    return (
      <div className="py-5 text-center">
        <div className="spinner-border text-primary" role="status">
          <span className="visually-hidden">Cargando...</span>
        </div>
        <p className="text-muted mt-2">Consultando estado del servicio de WhatsApp...</p>
      </div>
    );
  }

  if (status === "ERROR_API_DOWN") {
    return (
      <div className="text-center py-4">
        <div className="text-danger mb-3">
          <AlertCircle size={48} className="mx-auto" />
        </div>
        <h5 className="fw-bold text-danger">Servicio de WhatsApp no disponible</h5>
        <p className="text-muted max-w-md mx-auto small">
          No fue posible establecer conexión con el motor de Evolution API. Por favor verifica que el servicio esté ejecutándose en el servidor.
        </p>
        <button
          type="button"
          className="btn btn-outline-primary btn-sm mt-2 d-inline-flex align-items-center gap-1"
          onClick={checkStatus}
        >
          <RefreshCw size={14} />
          <span>Reintentar Conexión</span>
        </button>
      </div>
    );
  }

  if (status === "CONNECTED") {
    return (
      <div className="py-3">
        <div className="d-flex align-items-center gap-3 p-3 bg-light border border-success-subtle rounded-3 mb-4">
          <div className="bg-success text-white rounded-circle p-2 d-flex align-items-center justify-content-center" style={{ width: "44px", height: "44px" }}>
            <Check size={24} />
          </div>
          <div>
            <div className="d-flex align-items-center gap-2">
              <h6 className="mb-0 fw-bold text-success">Instancia Conectada y Operativa</h6>
              <span className="badge bg-success-subtle text-success border border-success-subtle">Online</span>
            </div>
            <p className="text-muted mb-0 small">
              Las notificaciones de pedidos se enviarán de forma automática a través de esta cuenta de WhatsApp.
            </p>
          </div>
        </div>

        {instanceInfo && (
          <div className="row g-3 mb-4">
            <div className="col-sm-6">
              <div className="p-3 border rounded bg-white">
                <small className="text-muted d-block">Número Conectado</small>
                <div className="d-flex align-items-center gap-2 mt-1">
                  <Smartphone size={16} className="text-secondary" />
                  <strong className="font-monospace">
                    {instanceInfo.phone_number ? `+${instanceInfo.phone_number}` : "Configurado en móvil"}
                  </strong>
                </div>
              </div>
            </div>
            <div className="col-sm-6">
              <div className="p-3 border rounded bg-white">
                <small className="text-muted d-block">Perfil / Nombre</small>
                <div className="d-flex align-items-center gap-2 mt-1">
                  <Phone size={16} className="text-secondary" />
                  <strong>{instanceInfo.profile_name || "Distribuidora Tridente"}</strong>
                </div>
              </div>
            </div>
          </div>
        )}

        <div className="d-flex gap-2">
          <button
            type="button"
            className="btn btn-outline-secondary btn-sm d-inline-flex align-items-center gap-1"
            onClick={checkStatus}
          >
            <RefreshCw size={14} />
            <span>Actualizar Estado</span>
          </button>
          <button
            type="button"
            className="btn btn-outline-danger btn-sm d-inline-flex align-items-center gap-1"
            onClick={handleDisconnect}
            disabled={loadingAction}
          >
            <LogOut size={14} />
            <span>Desvincular Dispositivo</span>
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="text-center py-4">
      <div className="mb-3">
        <Smartphone size={40} className="text-muted mx-auto" />
      </div>
      <h5 className="fw-bold mb-2">Vincular WhatsApp de la Empresa</h5>
      <p className="text-muted small mx-auto mb-4" style={{ maxWidth: "460px" }}>
        Genera un código QR y escanéalo desde la app de WhatsApp de tu teléfono en <strong>Dispositivos vinculados &gt; Vincular un dispositivo</strong>.
      </p>

      {status === "QR_READY" && qrBase64 ? (
        <div className="d-flex flex-column align-items-center my-3">
          <div className="p-3 bg-white border rounded shadow-sm">
            <img
              src={qrBase64}
              alt="Código QR WhatsApp"
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
  const [whatsappInfo, setWhatsappInfo] = useState(null);
  const [totalNotificacionesEnviadas, setTotalNotificacionesEnviadas] = useState(0);
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
    jwt_access_token_expire_minutes: 60,
  });

  useEffect(() => {
    loadSettings();
    loadTotalNotificaciones();
  }, []);

  const loadTotalNotificaciones = async () => {
    try {
      const response = await api.get("/log_correos?limit=1");
      const totalHeader = response.headers?.["x-total-count"];
      if (totalHeader !== undefined) {
        setTotalNotificacionesEnviadas(parseInt(totalHeader, 10) || 0);
      } else if (Array.isArray(response.data)) {
        setTotalNotificacionesEnviadas(response.data.length);
      }
    } catch {
      // Si falla, se mantiene en 0 o valor previo
    }
  };

  const loadSettings = async () => {
    setFetching(true);
    try {
      const data = await getSettings();
      setSettings((prev) => ({
        ...prev,
        ...data,
        smtp_port: data.smtp_port ? String(data.smtp_port) : "",
        jwt_access_token_expire_minutes: data.jwt_access_token_expire_minutes || 60,
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
        jwt_access_token_expire_minutes: settings.jwt_access_token_expire_minutes
          ? parseInt(settings.jwt_access_token_expire_minutes, 10)
          : 60,
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

  const [testingEmail, setTestingEmail] = useState(false);

  const handleTestEmail = async () => {
    if (!settings.smtp_host || !settings.smtp_username || !settings.smtp_password || !settings.smtp_from_email) {
      await Swal.fire({
        title: "Campos incompletos",
        text: "Para probar el envío, completa al menos Servidor, Usuario, Contraseña y Correo Remitente.",
        icon: "warning",
        confirmButtonText: "Entendido",
      });
      return;
    }

    const { value: email } = await Swal.fire({
      title: "Probar Envío de Correo",
      text: "Ingresa el correo del destinatario que recibirá el mensaje de prueba:",
      input: "email",
      inputPlaceholder: "ejemplo@correo.com",
      inputValue: settings.smtp_from_email || "",
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
          return "El formato de correo no es válido.";
        }
      },
    });

    if (!email) return;

    setTestingEmail(true);
    Swal.fire({
      title: "Enviando correo de prueba...",
      html: `Conectando con el servidor SMTP <b>${settings.smtp_host}</b> y enviando a <b>${email}</b>.`,
      allowOutsideClick: false,
      didOpen: () => {
        Swal.showLoading();
      },
    });

    try {
      const payload = {
        recipient: email.trim(),
        smtp_host: settings.smtp_host,
        smtp_port: settings.smtp_port ? parseInt(settings.smtp_port, 10) : null,
        smtp_username: settings.smtp_username,
        smtp_password: settings.smtp_password,
        smtp_from_email: settings.smtp_from_email,
        smtp_from_name: settings.smtp_from_name || "Distribuidora Tridente",
      };
      await sendTestEmail(payload);
      Swal.fire({
        icon: "success",
        title: "¡Correo enviado con éxito!",
        html: `<p>El mensaje de prueba se envió correctamente a <b>${email}</b>.</p><p class="text-muted small mb-0">Revisa tu bandeja de entrada (y la carpeta de spam o correo no deseado).</p>`,
        confirmButtonText: "Aceptar",
        confirmButtonColor: "#16a34a",
      });
    } catch (err) {
      const errorMsg =
        err.response?.data?.detail ||
        err.message ||
        "No fue posible enviar el correo de prueba. Verifica la configuración.";
      Swal.fire({
        icon: "error",
        title: "Error en la prueba SMTP",
        text: typeof errorMsg === "string" ? errorMsg : JSON.stringify(errorMsg),
        confirmButtonText: "Cerrar",
      });
    } finally {
      setTestingEmail(false);
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
            <p>Configuración de notificaciones de cobranza.</p>
          </div>
          <div className="summary-metric">
            {activeTab === "smtp" ? (
              <>
                <span className="fs-4 fw-bold">{isSmtpConfigured ? "Configurado" : "Pendiente"}</span>
                <small>Estado Correo (SMTP)</small>
              </>
            ) : activeTab === "whatsapp" ? (
              <>
                <span className="fs-4 fw-bold">
                  {whatsappInfo?.state === "CONNECTED" || whatsappInfo?.state === "open"
                    ? (whatsappInfo?.phone_number || "Vinculado")
                    : "No Vinculado"}
                </span>
                <small>
                  {whatsappInfo?.state === "CONNECTED" || whatsappInfo?.state === "open"
                    ? "WhatsApp Vinculado"
                    : "Estado WhatsApp"}
                </small>
              </>
            ) : activeTab === "notificaciones" ? (
              <>
                <span className="fs-4 fw-bold">{totalNotificacionesEnviadas}</span>
                <small>Notificaciones Enviadas</small>
              </>
            ) : (
              <>
                <span className="fs-4 fw-bold">{settings.jwt_access_token_expire_minutes || 60} min</span>
                <small>Expiración de Sesión</small>
              </>
            )}
          </div>
        </section>

        <section className="content-panel">
          <div className="panel-heading mb-3">
            <div>
              <h2>Parámetros y Servicios</h2>
              <p>Configura los servidores, canales de notificación y duración de sesiones.</p>
            </div>
            <span className="panel-count">
              {activeTab === "smtp"
                ? "SMTP"
                : activeTab === "whatsapp"
                ? "WhatsApp"
                : activeTab === "notificaciones"
                ? "Cobranza"
                : "Sesión"}
            </span>
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
            <button
              type="button"
              className={`settings-tab-btn ${activeTab === "notificaciones" ? "active" : ""}`}
              onClick={() => setActiveTab("notificaciones")}
            >
              <Bell size={17} />
              <span>Notificaciones</span>
            </button>
            <button
              type="button"
              className={`settings-tab-btn ${activeTab === "session" ? "active" : ""}`}
              onClick={() => setActiveTab("session")}
            >
              <Clock size={17} />
              <span>Ajuste de Sesión</span>
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

                  <div className="d-flex justify-content-between align-items-center mt-4 pt-2">
                    <button
                      type="button"
                      className="btn btn-outline-primary d-inline-flex align-items-center gap-2"
                      onClick={handleTestEmail}
                      disabled={loading || testingEmail}
                    >
                      <Send size={16} />
                      <span>{testingEmail ? "Probando..." : "Probar Envío de Correo"}</span>
                    </button>
                    <button type="submit" className="btn btn-primary d-inline-flex align-items-center gap-2" disabled={loading}>
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
                    <WhatsAppConnector onStatusUpdate={setWhatsappInfo} />
                  </div>
                </div>
              )}

              {activeTab === "notificaciones" && (
                <NotificacionesTab onUpdateCount={loadTotalNotificaciones} />
              )}

              {activeTab === "session" && (
                <form onSubmit={handleSubmit}>
                  <div className="settings-card">
                    <div className="settings-card-header">
                      <div>
                        <h3>Duración y Expiración de Sesión</h3>
                        <p>
                          Establece el tiempo de validez del token de inicio de sesión (JWT) para administradores y clientes.
                        </p>
                      </div>
                      <Clock size={18} className="text-primary" />
                    </div>
                    <div className="settings-card-body">
                      <div className="mb-3">
                        <label htmlFor="jwt_access_token_expire_minutes" className="form-label fw-bold">
                          Duración de la sesión (en minutos)
                        </label>
                        <div className="input-group" style={{ maxWidth: "340px" }}>
                          <input
                            id="jwt_access_token_expire_minutes"
                            type="number"
                            min="1"
                            max="525600"
                            step="1"
                            className="form-control"
                            name="jwt_access_token_expire_minutes"
                            value={settings.jwt_access_token_expire_minutes || ""}
                            onChange={handleInputChange}
                            required
                          />
                          <span className="input-group-text">minutos</span>
                        </div>
                        <small className="form-text text-muted mt-2 d-block">
                          Al expirar este tiempo, el usuario o cliente deberá ingresar nuevamente sus credenciales.
                        </small>
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
                          <span>Guardar Ajuste de Sesión</span>
                        </>
                      )}
                    </button>
                  </div>
                </form>
              )}
            </div>
          )}
        </section>
      </div>
    </>
  );
}
