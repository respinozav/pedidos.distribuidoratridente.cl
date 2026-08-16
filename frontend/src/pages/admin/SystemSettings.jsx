import React, { useState, useEffect } from "react";
import Swal from "sweetalert2";
import { Mail, MessageCircle, Save, CheckCircle2, Server, Send, ShieldCheck } from "lucide-react";
import { getSettings, updateSettings } from "../../services/settingsService";

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
              <span>WhatsApp</span>
              <span className="settings-badge ms-1">Pronto</span>
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
            <form onSubmit={handleSubmit}>
              {activeTab === "smtp" && (
                <>
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
                </>
              )}

              {activeTab === "whatsapp" && (
                <>
                  <div className="settings-info-box mb-4">
                    <MessageCircle size={22} />
                    <div>
                      <strong>Integración con WhatsApp Business API</strong>
                      <p>
                        Próximamente podrás activar notificaciones automáticas por WhatsApp para avisar a tus clientes cuando su pedido pase a estado <em>Despachado</em> o <em>Entregado</em>.
                      </p>
                    </div>
                  </div>

                  <div className="settings-card opacity-75">
                    <div className="settings-card-header">
                      <div>
                        <h3>Parámetros de API de WhatsApp</h3>
                        <p>Campos preparados para la próxima actualización.</p>
                      </div>
                      <ShieldCheck size={18} className="text-muted" />
                    </div>
                    <div className="settings-card-body">
                      <div className="settings-field-group">
                        <div className="settings-field">
                          <label htmlFor="whatsapp_phone">Número de WhatsApp</label>
                          <input
                            id="whatsapp_phone"
                            type="text"
                            className="form-control"
                            name="whatsapp_phone_number"
                            value={settings.whatsapp_phone_number || ""}
                            onChange={handleInputChange}
                            placeholder="+56912345678"
                            disabled
                          />
                          <small className="form-text">Número registrado en WhatsApp Cloud API.</small>
                        </div>
                        <div className="settings-field">
                          <label htmlFor="whatsapp_token">Token / API Key</label>
                          <input
                            id="whatsapp_token"
                            type="password"
                            className="form-control"
                            name="whatsapp_api_key"
                            value={settings.whatsapp_api_key || ""}
                            onChange={handleInputChange}
                            placeholder="EAAG..."
                            disabled
                          />
                          <small className="form-text">Token de acceso permanente del proveedor.</small>
                        </div>
                      </div>
                    </div>
                  </div>
                </>
              )}

              <div className="d-flex justify-content-end mt-4 pt-2">
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={loading || activeTab === "whatsapp"}
                >
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
        </section>
      </div>
    </>
  );
}
