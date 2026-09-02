import React, { useState, useEffect } from "react";
import Swal from "sweetalert2";
import {
  Bell,
  Clock,
  Mail,
  Calendar,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
  FileText,
} from "lucide-react";
import { api } from "../../services/api";
import ModalPlantillaEmail from "../../components/admin/ModalPlantillaEmail";

export default function NotificacionesTab({ onUpdateCount }) {
  const [config, setConfig] = useState(null);
  const [logs, setLogs] = useState([]);
  const [loadingConfig, setLoadingConfig] = useState(true);
  const [loadingLogs, setLoadingLogs] = useState(false);
  const [saving, setSaving] = useState(false);
  const [modalState, setModalState] = useState({ open: false, tipo: null });

  const cargarConfig = async () => {
    try {
      setLoadingConfig(true);
      const response = await api.get("/configuracion_avisos");
      const data = Array.isArray(response.data) ? response.data[0] : response.data;
      setConfig(
        data || {
          id: 1,
          hora_envio: "09:00:00",
          asunto_recordatorio: "Recordatorio: Tu crédito vencerá mañana - Distribuidora Tridente",
          plantilla_recordatorio:
            "Hola {{nombre}}, le recordamos que su crédito por {{dias_credito}} días vencerá el {{fecha_vencimiento}}. Favor coordinar el pago.",
          asunto_aviso: "Aviso: Tu crédito vence hoy - Distribuidora Tridente",
          plantilla_aviso:
            "Estimado/a {{nombre}}, le informamos que su crédito vence hoy {{fecha_vencimiento}}. Favor regularizar a la brevedad.",
          asunto_vencido: "Urgente: Tu crédito se encuentra VENCIDO - Distribuidora Tridente",
          plantilla_vencido:
            "Estimado/a {{nombre}}, le informamos que su crédito por {{dias_credito}} días se encuentra VENCIDO desde el {{fecha_vencimiento}} ({{dias_mora}} días de mora). Favor regularizar su saldo a la brevedad.",
          activo: true,
        }
      );
    } catch {
      // Fallback por defecto si aún no se inicializa la tabla
      setConfig({
        id: 1,
        hora_envio: "09:00:00",
        asunto_recordatorio: "Recordatorio: Tu crédito vencerá mañana - Distribuidora Tridente",
        plantilla_recordatorio:
          "Hola {{nombre}}, le recordamos que su crédito por {{dias_credito}} días vencerá el {{fecha_vencimiento}}. Favor coordinar el pago.",
        asunto_aviso: "Aviso: Tu crédito vence hoy - Distribuidora Tridente",
        plantilla_aviso:
          "Estimado/a {{nombre}}, le informamos que su crédito vence hoy {{fecha_vencimiento}}. Favor regularizar a la brevedad.",
        asunto_vencido: "Urgente: Tu crédito se encuentra VENCIDO - Distribuidora Tridente",
        plantilla_vencido:
          "Estimado/a {{nombre}}, le informamos que su crédito por {{dias_credito}} días se encuentra VENCIDO desde el {{fecha_vencimiento}} ({{dias_mora}} días de mora). Favor regularizar su saldo a la brevedad.",
        activo: true,
      });
    } finally {
      setLoadingConfig(false);
    }
  };

  const cargarLogs = async () => {
    try {
      setLoadingLogs(true);
      const response = await api.get("/log_correos?limit=30");
      setLogs(Array.isArray(response.data) ? response.data : []);
      if (typeof onUpdateCount === "function") {
        onUpdateCount();
      }
    } catch {
      setLogs([]);
    } finally {
      setLoadingLogs(false);
    }
  };

  useEffect(() => {
    cargarConfig();
    cargarLogs();
  }, []);

  const actualizarConfig = async (patchData) => {
    try {
      setSaving(true);
      const response = await api.patch("/configuracion_avisos", patchData);
      setConfig(response.data || ((prev) => ({ ...prev, ...patchData })));
      Swal.fire({
        toast: true,
        position: "top-end",
        icon: "success",
        title: "Ajuste de notificación guardado",
        showConfirmButton: false,
        timer: 2000,
      });
    } catch (err) {
      const msg = err.response?.data?.detail || "No se pudo guardar la configuración de avisos.";
      Swal.fire({
        icon: "error",
        title: "Error al actualizar",
        text: typeof msg === "string" ? msg : JSON.stringify(msg),
      });
    } finally {
      setSaving(false);
    }
  };

  const handleGuardarPlantilla = async ({ asunto, cuerpo }) => {
    let payload = {};
    if (modalState.tipo === "RECORDATORIO") {
      payload = { asunto_recordatorio: asunto, plantilla_recordatorio: cuerpo };
    } else if (modalState.tipo === "AVISO") {
      payload = { asunto_aviso: asunto, plantilla_aviso: cuerpo };
    } else if (modalState.tipo === "VENCIDO") {
      payload = { asunto_vencido: asunto, plantilla_vencido: cuerpo };
    }

    await actualizarConfig(payload);
    setModalState({ open: false, tipo: null });
  };

  if (loadingConfig) {
    return (
      <div className="py-5 text-center text-secondary">
        <div className="spinner-border spinner-border-sm text-primary me-2" role="status" />
        <span>Cargando configuración de avisos...</span>
      </div>
    );
  }

  return (
    <div className="d-flex flex-column gap-4">
      {/* SECCIÓN 1: Horario de envío y Switch de Activación */}
      <div className="row g-3">
        <div className="col-lg-4 col-md-6">
          <div className="settings-card h-100 mb-0">
            <div className="settings-card-header pb-2">
              <div>
                <h4 className="fs-6 fw-bold mb-1">Hora de Ejecución</h4>
                <p className="small text-muted mb-0">Disparo automático diario de correos.</p>
              </div>
              <Clock size={20} className="text-primary" />
            </div>
            <div className="settings-card-body pt-2">
              <div className="input-group">
                <input
                  type="time"
                  step="1"
                  className="form-control"
                  value={config?.hora_envio ? config.hora_envio.slice(0, 8) : "09:00:00"}
                  onChange={(e) => {
                    const val = e.target.value;
                    setConfig((prev) => ({ ...prev, hora_envio: val }));
                  }}
                  onBlur={(e) => {
                    if (e.target.value) {
                      actualizarConfig({ hora_envio: e.target.value });
                    }
                  }}
                  disabled={saving}
                />
              </div>
              <small className="text-muted mt-2 d-block" style={{ fontSize: "0.78rem" }}>
                El servidor evaluará créditos a vencer a esta hora.
              </small>
            </div>
          </div>
        </div>

        <div className="col-lg-8 col-md-6">
          <div className="settings-card h-100 mb-0 d-flex flex-column justify-content-between">
            <div className="settings-card-header pb-2">
              <div>
                <div className="d-flex align-items-center gap-2">
                  <h4 className="fs-6 fw-bold mb-0">Estado del Job Automático (pg_cron)</h4>
                  <span
                    className={`badge ${
                      config?.activo
                        ? "bg-success-subtle text-success border border-success-subtle"
                        : "bg-secondary-subtle text-secondary"
                    }`}
                  >
                    {config?.activo ? "Activo" : "Pausado"}
                  </span>
                </div>
                <p className="small text-muted mt-1 mb-0">
                  Habilita o suspende el despacho automático de recordatorios preventivos y avisos de cobro.
                </p>
              </div>
              <div className="form-check form-switch fs-4 mb-0">
                <input
                  className="form-check-input"
                  type="checkbox"
                  role="switch"
                  checked={Boolean(config?.activo)}
                  onChange={(e) => actualizarConfig({ activo: e.target.checked })}
                  disabled={saving}
                />
              </div>
            </div>
            <div className="settings-card-body pt-2">
              <small className="text-muted d-block" style={{ fontSize: "0.78rem" }}>
                {config?.activo
                  ? `✓ Los correos se enviarán automáticamente a las ${config?.hora_envio ? config.hora_envio.slice(0, 5) : "09:00"} hrs.`
                  : "⚠ Los envíos automáticos se encuentran en pausa."}
              </small>
            </div>
          </div>
        </div>
      </div>

      {/* SECCIÓN 2: Gestión de Plantillas con Modales */}
      <div>
        <div className="d-flex align-items-center justify-content-between mb-3">
          <h4 className="fs-6 fw-bold mb-0 d-flex align-items-center gap-2">
            <Mail size={18} className="text-primary" />
            <span>Plantillas de Correos de Cobranza</span>
          </h4>
        </div>

        <div className="row g-3">
          {/* Card Recordatorio Preventivo (VERDE) */}
          <div className="col-lg-4 col-md-6">
            <div className="settings-card h-100 mb-0">
              <div className="settings-card-header pb-2">
                <div className="d-flex align-items-center gap-2">
                  <span className="p-1 bg-success-subtle text-success rounded">
                    <Calendar size={18} />
                  </span>
                  <div>
                    <h5 className="fs-6 fw-bold mb-0">Recordatorio Preventivo</h5>
                    <small className="badge bg-success-subtle text-success border border-success-subtle mt-1">
                      1 día antes del vencimiento
                    </small>
                  </div>
                </div>
              </div>
              <div className="settings-card-body pt-2">
                <p className="small text-muted mb-2 font-monospace" style={{ fontSize: "0.82rem" }}>
                  <strong>Asunto:</strong> {config?.asunto_recordatorio}
                </p>
                <div
                  className="p-3 rounded-3 font-monospace small mb-3 text-truncate"
                  style={{
                    maxHeight: "75px",
                    overflow: "hidden",
                    backgroundColor: "#f0fdf4",
                    border: "1px solid #bbf7d0",
                    borderLeft: "4px solid #16a34a",
                    color: "#14532d",
                  }}
                >
                  {config?.plantilla_recordatorio}
                </div>
                <button
                  type="button"
                  className="btn btn-outline-success btn-sm w-100 d-flex align-items-center justify-content-center gap-2"
                  onClick={() => setModalState({ open: true, tipo: "RECORDATORIO" })}
                >
                  <FileText size={15} />
                  <span>Editar Plantilla Recordatorio</span>
                </button>
              </div>
            </div>
          </div>

          {/* Card Aviso Mismo Día (AMARILLO) */}
          <div className="col-lg-4 col-md-6">
            <div className="settings-card h-100 mb-0">
              <div className="settings-card-header pb-2">
                <div className="d-flex align-items-center gap-2">
                  <span className="p-1 bg-warning-subtle text-warning rounded">
                    <Bell size={18} />
                  </span>
                  <div>
                    <h5 className="fs-6 fw-bold mb-0">Aviso de Vencimiento</h5>
                    <small className="badge bg-warning-subtle text-warning border border-warning-subtle mt-1">
                      El mismo día de vencimiento
                    </small>
                  </div>
                </div>
              </div>
              <div className="settings-card-body pt-2">
                <p className="small text-muted mb-2 font-monospace" style={{ fontSize: "0.82rem" }}>
                  <strong>Asunto:</strong> {config?.asunto_aviso}
                </p>
                <div
                  className="p-3 rounded-3 font-monospace small mb-3 text-truncate"
                  style={{
                    maxHeight: "75px",
                    overflow: "hidden",
                    backgroundColor: "#fffbeb",
                    border: "1px solid #fde68a",
                    borderLeft: "4px solid #d97706",
                    color: "#78350f",
                  }}
                >
                  {config?.plantilla_aviso}
                </div>
                <button
                  type="button"
                  className="btn btn-outline-warning btn-sm w-100 d-flex align-items-center justify-content-center gap-2 text-dark"
                  onClick={() => setModalState({ open: true, tipo: "AVISO" })}
                >
                  <FileText size={15} />
                  <span>Editar Plantilla Aviso</span>
                </button>
              </div>
            </div>
          </div>

          {/* Card Crédito Vencido / En Mora (ROJO) */}
          <div className="col-lg-4 col-md-12">
            <div className="settings-card h-100 mb-0">
              <div className="settings-card-header pb-2">
                <div className="d-flex align-items-center gap-2">
                  <span className="p-1 bg-danger-subtle text-danger rounded">
                    <AlertCircle size={18} />
                  </span>
                  <div>
                    <h5 className="fs-6 fw-bold mb-0">Crédito Vencido / En Mora</h5>
                    <small className="badge bg-danger-subtle text-danger border border-danger-subtle mt-1">
                      Créditos vencidos impagos
                    </small>
                  </div>
                </div>
              </div>
              <div className="settings-card-body pt-2">
                <p className="small text-muted mb-2 font-monospace" style={{ fontSize: "0.82rem" }}>
                  <strong>Asunto:</strong> {config?.asunto_vencido}
                </p>
                <div
                  className="p-3 rounded-3 font-monospace small mb-3 text-truncate"
                  style={{
                    maxHeight: "75px",
                    overflow: "hidden",
                    backgroundColor: "#fef2f2",
                    border: "1px solid #fecaca",
                    borderLeft: "4px solid #dc2626",
                    color: "#7f1d1d",
                  }}
                >
                  {config?.plantilla_vencido}
                </div>
                <button
                  type="button"
                  className="btn btn-outline-danger btn-sm w-100 d-flex align-items-center justify-content-center gap-2"
                  onClick={() => setModalState({ open: true, tipo: "VENCIDO" })}
                >
                  <FileText size={15} />
                  <span>Editar Plantilla Vencido</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* SECCIÓN 3: Tabla de Historial de Correos Enviados */}
      <div className="settings-card mb-0">
        <div className="settings-card-header d-flex align-items-center justify-content-between pb-3">
          <div>
            <h4 className="fs-6 fw-bold mb-1 d-flex align-items-center gap-2">
              <Clock size={18} className="text-primary" />
              <span>Historial de Correos Despachados</span>
            </h4>
            <p className="small text-muted mb-0">
              Registro auditado de avisos y recordatorios emitidos por el sistema.
            </p>
          </div>
          <button
            type="button"
            className="btn btn-outline-secondary btn-sm d-inline-flex align-items-center gap-1"
            onClick={cargarLogs}
            disabled={loadingLogs}
          >
            <RefreshCw size={14} className={loadingLogs ? "spinner-border spinner-border-sm" : ""} />
            <span>Actualizar</span>
          </button>
        </div>

        <div className="settings-card-body p-0">
          <div className="table-responsive">
            <table className="table table-hover align-middle mb-0" style={{ fontSize: "0.85rem" }}>
              <thead className="table-light text-uppercase" style={{ fontSize: "0.75rem", letterSpacing: "0.04em" }}>
                <tr>
                  <th className="px-3 py-2.5">Fecha / Hora</th>
                  <th className="px-3 py-2.5">Destinatario</th>
                  <th className="px-3 py-2.5">Tipo</th>
                  <th className="px-3 py-2.5">Asunto</th>
                  <th className="px-3 py-2.5 text-end">Estado</th>
                </tr>
              </thead>
              <tbody>
                {logs.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="text-center py-4 text-muted">
                      No hay registros de correos de cobranza enviados todavía.
                    </td>
                  </tr>
                ) : (
                  logs.map((log) => (
                    <tr key={log.id}>
                      <td className="px-3 py-2 text-nowrap font-monospace text-muted">
                        {log.enviado_el ? new Date(log.enviado_el).toLocaleString("es-CL") : "-"}
                      </td>
                      <td className="px-3 py-2 fw-semibold text-dark">{log.destinatario}</td>
                      <td className="px-3 py-2">
                        <span
                          className={`badge ${
                            log.tipo === "RECORDATORIO"
                              ? "bg-success-subtle text-success border border-success-subtle"
                              : log.tipo === "AVISO_HOY" || log.tipo === "AVISO"
                              ? "bg-warning-subtle text-warning border border-warning-subtle"
                              : "bg-danger-subtle text-danger border border-danger-subtle"
                          }`}
                          style={{ fontSize: "0.75rem" }}
                        >
                          {log.tipo}
                        </span>
                      </td>
                      <td className="px-3 py-2 text-truncate text-secondary" style={{ maxWidth: "260px" }}>
                        {log.asunto}
                      </td>
                      <td className="px-3 py-2 text-end">
                        <span className="badge bg-success-subtle text-success border border-success-subtle d-inline-flex align-items-center gap-1">
                          <CheckCircle2 size={12} /> {log.estado || "ENVIADO"}
                        </span>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Modal de edición */}
      <ModalPlantillaEmail
        isOpen={modalState.open}
        onClose={() => setModalState({ open: false, tipo: null })}
        tipo={modalState.tipo}
        titulo={
          modalState.tipo === "RECORDATORIO"
            ? "Plantilla: Recordatorio (1 día antes)"
            : modalState.tipo === "VENCIDO"
            ? "Plantilla: Cobranza Crédito Vencido / En Mora"
            : "Plantilla: Aviso de Vencimiento (Mismo día)"
        }
        asuntoInicial={
          modalState.tipo === "RECORDATORIO"
            ? config?.asunto_recordatorio
            : modalState.tipo === "VENCIDO"
            ? config?.asunto_vencido
            : config?.asunto_aviso
        }
        cuerpoInicial={
          modalState.tipo === "RECORDATORIO"
            ? config?.plantilla_recordatorio
            : modalState.tipo === "VENCIDO"
            ? config?.plantilla_vencido
            : config?.plantilla_aviso
        }
        onGuardar={handleGuardarPlantilla}
        cargando={saving}
      />
    </div>
  );
}
