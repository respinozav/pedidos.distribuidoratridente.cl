import React, { useState, useEffect } from "react";
import Swal from "sweetalert2";
import {
  Bell,
  ShoppingCart,
  CheckCircle2,
} from "lucide-react";
import NotificacionesTab from "./NotificacionesTab";
import AjusteCarroComprasTab from "./AjusteCarroComprasTab";
import StockAlertBell from "../../components/admin/StockAlertBell";
import { api } from "../../services/api";
import { getSettings, updateSettings } from "../../services/settingsService";

export default function CommercialSettings() {
  const [activeTab, setActiveTab] = useState("notificaciones");
  const [loading, setLoading] = useState(false);
  const [fetching, setFetching] = useState(true);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [totalNotificacionesEnviadas, setTotalNotificacionesEnviadas] = useState(0);
  const [settings, setSettings] = useState({
    carro_compras_expira_horas: 24,
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
        carro_compras_expira_horas: data.carro_compras_expira_horas || 24,
      }));
    } catch {
      setError("No fue posible cargar los ajustes comerciales.");
      Swal.fire("Error", "No fue posible cargar los ajustes comerciales.", "error");
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
    if (e && e.preventDefault) e.preventDefault();
    setLoading(true);
    setNotice("");
    setError("");
    try {
      const payload = {
        ...settings,
        carro_compras_expira_horas: settings.carro_compras_expira_horas
          ? parseInt(settings.carro_compras_expira_horas, 10)
          : 24,
      };
      await updateSettings(payload);
      setNotice("Ajustes comerciales actualizados correctamente.");
      Swal.fire({
        icon: "success",
        title: "Ajustes guardados",
        text: "La configuración comercial se ha actualizado correctamente.",
        timer: 2000,
        showConfirmButton: false,
      });
    } catch (err) {
      const errorMsg =
        err.response?.data?.detail ||
        "No fue posible guardar los ajustes comerciales.";
      setError(errorMsg);
      Swal.fire("Error al guardar", errorMsg, "error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <header className="admin-topbar">
        <div className="topbar-title">
          <p className="eyebrow mb-1">CONFIGURACION</p>
          <h1>Comerciales</h1>
        </div>
        <div className="topbar-actions">
          <span className="topbar-date d-none d-sm-inline">Parámetros comerciales</span>
          <StockAlertBell />
        </div>
      </header>

      <div className="admin-content">
        <section className="admin-summary">
          <div>
            <p className="eyebrow">PARAMETROS</p>
            <h2>Configuración Comercial</h2>
            <p>Configuración de notificaciones de cobranza y carros de compra.</p>
          </div>
          <div className="summary-metric">
            {activeTab === "notificaciones" ? (
              <>
                <span className="fs-4 fw-bold">{totalNotificacionesEnviadas}</span>
                <small>Notificaciones Enviadas</small>
              </>
            ) : (
              <>
                <span className="fs-4 fw-bold">{settings.carro_compras_expira_horas || 24} hrs</span>
                <small>Expiración de Carros</small>
              </>
            )}
          </div>
        </section>

        <section className="content-panel">
          <div className="panel-heading mb-3">
            <div>
              <h2>Parámetros Comerciales</h2>
              <p>Gestiona las notificaciones de cobranza y la expiración de carros de compra.</p>
            </div>
            <span className="panel-count">
              {activeTab === "notificaciones" ? "Cobranza" : "Carro de Compras"}
            </span>
          </div>

          <div className="settings-tab-bar">
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
              className={`settings-tab-btn ${activeTab === "carro_compras" ? "active" : ""}`}
              onClick={() => setActiveTab("carro_compras")}
            >
              <ShoppingCart size={17} />
              <span>Ajustes Carros de Compra</span>
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
            <p className="text-secondary py-3">Cargando ajustes comerciales...</p>
          ) : (
            <div>
              {activeTab === "notificaciones" && (
                <NotificacionesTab onUpdateCount={loadTotalNotificaciones} />
              )}

              {activeTab === "carro_compras" && (
                <AjusteCarroComprasTab
                  settings={settings}
                  onSettingsChange={handleInputChange}
                  onSaveSettings={handleSubmit}
                  saving={loading}
                />
              )}
            </div>
          )}
        </section>
      </div>
    </>
  );
}
