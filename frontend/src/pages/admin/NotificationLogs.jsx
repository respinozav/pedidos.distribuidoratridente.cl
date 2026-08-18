import { useEffect, useState } from "react";
import {
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Copy,
  Eye,
  FileText,
  Filter,
  Mail,
  MessageSquare,
  RefreshCw,
  RotateCcw,
  Search,
  Send,
  X,
} from "lucide-react";
import Swal from "sweetalert2";
import { api } from "../../services/api";

const dateFormatter = new Intl.DateTimeFormat("es-CL", {
  dateStyle: "short",
  timeStyle: "medium",
});

export default function NotificationLogs() {
  const [logs, setLogs] = useState([]);
  const [stats, setStats] = useState({
    total: 0,
    whatsapp_enviados: 0,
    whatsapp_fallidos: 0,
    email_enviados: 0,
    email_fallidos: 0,
    omitidos: 0,
  });
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const pageSize = 20;

  const [filters, setFilters] = useState({
    canal: "",
    estado: "",
    search: "",
    desde: "",
    hasta: "",
  });

  const [loading, setLoading] = useState(true);
  const [selectedLog, setSelectedLog] = useState(null);
  const [retrying, setRetrying] = useState(false);

  async function loadStats() {
    try {
      const { data } = await api.get("/admin/pedidos/logs/stats");
      setStats(data);
    } catch {
      // Ignorar error secundario de stats
    }
  }

  async function loadLogs(targetPage = page) {
    setLoading(true);
    try {
      const params = {
        page: targetPage,
        page_size: pageSize,
      };
      if (filters.canal) params.canal = filters.canal;
      if (filters.estado) params.estado = filters.estado;
      if (filters.search.trim()) params.search = filters.search.trim();
      if (filters.desde) params.desde = filters.desde;
      if (filters.hasta) params.hasta = filters.hasta;

      const { data } = await api.get("/admin/pedidos/logs", { params });
      setLogs(data.items);
      setTotal(data.total);
      setPage(data.page);
    } catch {
      Swal.fire({
        icon: "error",
        title: "Error al cargar logs",
        text: "No fue posible obtener el registro de notificaciones.",
      });
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadStats();
    loadLogs(1);
  }, [filters.canal, filters.estado, filters.desde, filters.hasta]);

  function handleSearchSubmit(e) {
    e.preventDefault();
    loadLogs(1);
  }

  function clearFilters() {
    setFilters({
      canal: "",
      estado: "",
      search: "",
      desde: "",
      hasta: "",
    });
    setPage(1);
  }

  async function handleRetry(orderId) {
    if (!orderId) return;
    setRetrying(true);
    try {
      await api.post(`/admin/pedidos/${orderId}/reintentar-notificaciones`);
      Swal.fire({
        icon: "success",
        title: "Reintento iniciado",
        text: "Las notificaciones se están procesando nuevamente en segundo plano.",
        timer: 2500,
        showConfirmButton: false,
      });
      // Recargar stats y logs tras 1.5s
      setTimeout(() => {
        loadStats();
        loadLogs(page);
      }, 1500);
    } catch (err) {
      Swal.fire({
        icon: "error",
        title: "No fue posible reintentar",
        text: err.response?.data?.detail ?? "Ocurrió un error al solicitar el reintento.",
      });
    } finally {
      setRetrying(false);
    }
  }

  function copyToClipboard(text) {
    navigator.clipboard.writeText(text);
    Swal.fire({
      toast: true,
      position: "top-end",
      icon: "success",
      title: "Copiado al portapapeles",
      showConfirmButton: false,
      timer: 1500,
    });
  }

  function renderChannelBadge(canal) {
    if (canal === "WHATSAPP") {
      return (
        <span className="badge-channel badge-whatsapp">
          <MessageSquare size={14} /> WhatsApp
        </span>
      );
    }
    if (canal === "EMAIL_ADMIN") {
      return (
        <span className="badge-channel badge-email-admin">
          <Mail size={14} /> Correo Admin
        </span>
      );
    }
    if (canal === "EMAIL_CLIENTE") {
      return (
        <span className="badge-channel badge-email-client">
          <Mail size={14} /> Correo Cliente
        </span>
      );
    }
    return (
      <span className="badge-channel badge-system">
        <FileText size={14} /> Sistema
      </span>
    );
  }

  function renderStatusBadge(estado) {
    if (estado === "ENVIADO") {
      return (
        <span className="badge-status-pill status-success">
          <CheckCircle2 size={13} /> Enviado
        </span>
      );
    }
    if (estado === "FALLIDO") {
      return (
        <span className="badge-status-pill status-failed">
          <AlertCircle size={13} /> Fallido
        </span>
      );
    }
    return (
      <span className="badge-status-pill status-skipped">
        <AlertTriangle size={13} /> Omitido
      </span>
    );
  }

  const totalPages = Math.ceil(total / pageSize) || 1;

  return (
    <>
      <header className="admin-topbar">
        <div className="topbar-title">
          <p className="eyebrow mb-1">AUDITORIA & NOTIFICACIONES</p>
          <h1>Logs de Envíos</h1>
        </div>
        <div className="topbar-actions">
          <button
            className="btn btn-outline-secondary d-flex align-items-center gap-2"
            onClick={() => {
              loadStats();
              loadLogs(page);
            }}
            disabled={loading}
          >
            <RefreshCw size={16} className={loading ? "animate-spin" : ""} />
            <span>Actualizar</span>
          </button>
        </div>
      </header>

      <div className="admin-content">
        {/* Tarjetas de Métricas Resumen */}
        <section className="dashboard-metrics mb-4">
          <article className="log-stat-card">
            <span>TOTAL EVENTOS</span>
            <strong>{stats.total}</strong>
            <small>Auditorías registradas</small>
          </article>
          <article className="log-stat-card border-success-subtle">
            <span className="text-success">WHATSAPP ENVIADOS</span>
            <strong className="text-success">{stats.whatsapp_enviados}</strong>
            <small>
              {stats.whatsapp_fallidos > 0 ? (
                <span className="text-danger fw-bold">{stats.whatsapp_fallidos} fallidos</span>
              ) : (
                "0 fallidos"
              )}
            </small>
          </article>
          <article className="log-stat-card border-primary-subtle">
            <span className="text-primary">CORREOS ENVIADOS</span>
            <strong className="text-primary">{stats.email_enviados}</strong>
            <small>
              {stats.email_fallidos > 0 ? (
                <span className="text-danger fw-bold">{stats.email_fallidos} fallidos</span>
              ) : (
                "0 fallidos"
              )}
            </small>
          </article>
          <article className="log-stat-card border-warning-subtle">
            <span className="text-warning-emphasis">NOTIFICACIONES OMITIDAS</span>
            <strong className="text-warning-emphasis">{stats.omitidos}</strong>
            <small>Sin configurar o sin teléfono</small>
          </article>
        </section>

        {/* Panel Principal */}
        <section className="content-panel">
          <div className="panel-heading">
            <div>
              <h2>Historial y Auditoría de Notificaciones</h2>
              <p>Revisa el estado de entrega en tiempo real de cada WhatsApp y correo electrónico.</p>
            </div>
            <span className="panel-count">{total} registros</span>
          </div>

          {/* Filtros */}
          <div className="order-history-filters log-filters mt-3">
            <label>
              Canal
              <select
                className="form-select"
                value={filters.canal}
                onChange={(e) => setFilters((curr) => ({ ...curr, canal: e.target.value }))}
              >
                <option value="">Todos los canales</option>
                <option value="WHATSAPP">WhatsApp</option>
                <option value="EMAIL_ADMIN">Correo Administrador</option>
                <option value="EMAIL_CLIENTE">Correo Cliente</option>
                <option value="SISTEMA">Sistema</option>
              </select>
            </label>

            <label>
              Estado
              <select
                className="form-select"
                value={filters.estado}
                onChange={(e) => setFilters((curr) => ({ ...curr, estado: e.target.value }))}
              >
                <option value="">Todos los estados</option>
                <option value="ENVIADO">Enviado (Exitoso)</option>
                <option value="FALLIDO">Fallido (Error)</option>
                <option value="OMITIDO">Omitido</option>
              </select>
            </label>

            <label className="flex-grow-1">
              Búsqueda
              <form onSubmit={handleSearchSubmit} className="d-flex gap-2">
                <input
                  className="form-control"
                  type="search"
                  placeholder="Destinatario, error, mensaje..."
                  value={filters.search}
                  onChange={(e) => setFilters((curr) => ({ ...curr, search: e.target.value }))}
                />
                <button className="btn btn-outline-primary" type="submit">
                  <Search size={16} />
                </button>
              </form>
            </label>

            <label>
              Desde
              <input
                className="form-control"
                type="date"
                value={filters.desde}
                onChange={(e) => setFilters((curr) => ({ ...curr, desde: e.target.value }))}
              />
            </label>

            <label>
              Hasta
              <input
                className="form-control"
                type="date"
                value={filters.hasta}
                onChange={(e) => setFilters((curr) => ({ ...curr, hasta: e.target.value }))}
              />
            </label>

            {(filters.canal || filters.estado || filters.search || filters.desde || filters.hasta) && (
              <div className="d-flex align-items-end">
                <button className="btn btn-link text-danger p-2" type="button" onClick={clearFilters}>
                  Limpiar
                </button>
              </div>
            )}
          </div>

          {/* Tabla de Logs */}
          {loading ? (
            <div className="p-5 text-center text-secondary">
              <RefreshCw size={24} className="animate-spin mb-2" />
              <p>Cargando auditoría de notificaciones...</p>
            </div>
          ) : logs.length ? (
            <>
              <div className="table-responsive mt-4">
                <table className="table table-hover align-middle log-table">
                  <thead>
                    <tr>
                      <th>Fecha / Hora</th>
                      <th>Pedido</th>
                      <th>Canal</th>
                      <th>Destinatario</th>
                      <th>Estado</th>
                      <th>Duración</th>
                      <th>Mensaje / Detalle</th>
                      <th className="text-end">Acciones</th>
                    </tr>
                  </thead>
                  <tbody>
                    {logs.map((log) => (
                      <tr key={log.id} className={log.estado === "FALLIDO" ? "table-danger-subtle" : ""}>
                        <td className="text-nowrap font-monospace text-secondary small">
                          {log.created_at ? dateFormatter.format(new Date(log.created_at)) : "-"}
                        </td>
                        <td>
                          {log.pedido_id ? (
                            <span className="badge bg-light text-dark border font-monospace">
                              #{log.pedido_id.slice(0, 8).toUpperCase()}
                            </span>
                          ) : (
                            <span className="text-muted small">-</span>
                          )}
                        </td>
                        <td>{renderChannelBadge(log.canal)}</td>
                        <td className="fw-semibold text-truncate" style={{ maxWidth: "200px" }} title={log.destinatario}>
                          {log.destinatario}
                        </td>
                        <td>{renderStatusBadge(log.estado)}</td>
                        <td className="text-nowrap small text-muted">
                          {log.duracion_ms != null ? (
                            <span className="d-inline-flex align-items-center gap-1">
                              <Clock size={12} />
                              {log.duracion_ms >= 1000
                                ? `${(log.duracion_ms / 1000).toFixed(2)}s`
                                : `${log.duracion_ms}ms`}
                            </span>
                          ) : (
                            "-"
                          )}
                        </td>
                        <td className="small text-truncate" style={{ maxWidth: "260px" }} title={log.error || log.mensaje}>
                          {log.error ? (
                            <span className="text-danger fw-semibold">{log.mensaje || log.error}</span>
                          ) : (
                            <span className="text-secondary">{log.mensaje || "-"}</span>
                          )}
                        </td>
                        <td className="text-end">
                          <button
                            className="icon-button category-edit"
                            type="button"
                            onClick={() => setSelectedLog(log)}
                            aria-label="Ver detalle del log"
                            title="Ver detalle completo"
                          >
                            <Eye size={16} />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Paginación */}
              <div className="d-flex justify-content-between align-items-center mt-3 pt-3 border-top">
                <span className="text-secondary small">
                  Página {page} de {totalPages} ({total} eventos totales)
                </span>
                <div className="d-flex gap-2">
                  <button
                    className="btn btn-outline-secondary btn-sm"
                    disabled={page <= 1}
                    onClick={() => {
                      const newPage = page - 1;
                      setPage(newPage);
                      loadLogs(newPage);
                    }}
                  >
                    Anterior
                  </button>
                  <button
                    className="btn btn-outline-secondary btn-sm"
                    disabled={page >= totalPages}
                    onClick={() => {
                      const newPage = page + 1;
                      setPage(newPage);
                      loadLogs(newPage);
                    }}
                  >
                    Siguiente
                  </button>
                </div>
              </div>
            </>
          ) : (
            <div className="p-5 text-center text-secondary">
              <FileText size={36} className="text-muted mb-3 opacity-50" />
              <h5>No hay registros de notificaciones</h5>
              <p className="mb-0">No se encontraron logs que coincidan con los filtros seleccionados.</p>
            </div>
          )}
        </section>
      </div>

      {/* Modal de Detalle del Log */}
      {selectedLog && (
        <div className="modal-backdrop-custom">
          <section className="category-modal log-detail-modal" role="dialog" aria-modal="true">
            <header>
              <div>
                <p className="eyebrow">DETALLE DE AUDITORIA</p>
                <h2>Registro de Notificación</h2>
              </div>
              <button
                className="icon-button"
                type="button"
                onClick={() => setSelectedLog(null)}
                aria-label="Cerrar detalle"
              >
                <X size={19} />
              </button>
            </header>

            <div className="modal-body-custom">
              {/* Resumen Superior */}
              <div className="log-detail-meta-grid">
                <div>
                  <small className="text-muted d-block">ID de Registro</small>
                  <span className="font-monospace small">{selectedLog.id}</span>
                </div>
                <div>
                  <small className="text-muted d-block">Fecha y Hora</small>
                  <span>
                    {selectedLog.created_at ? dateFormatter.format(new Date(selectedLog.created_at)) : "-"}
                  </span>
                </div>
                <div>
                  <small className="text-muted d-block">Canal</small>
                  {renderChannelBadge(selectedLog.canal)}
                </div>
                <div>
                  <small className="text-muted d-block">Estado</small>
                  {renderStatusBadge(selectedLog.estado)}
                </div>
                <div>
                  <small className="text-muted d-block">Destinatario</small>
                  <strong>{selectedLog.destinatario}</strong>
                </div>
                <div>
                  <small className="text-muted d-block">Pedido Asociado</small>
                  {selectedLog.pedido_id ? (
                    <span className="badge bg-light text-dark border font-monospace">
                      #{selectedLog.pedido_id.slice(0, 8).toUpperCase()}
                    </span>
                  ) : (
                    "Sin pedido"
                  )}
                </div>
                <div>
                  <small className="text-muted d-block">Duración de Ejecución</small>
                  <span className="d-flex align-items-center gap-1 font-monospace">
                    <Clock size={14} />
                    {selectedLog.duracion_ms != null ? `${selectedLog.duracion_ms} ms` : "N/D"}
                  </span>
                </div>
                <div>
                  <small className="text-muted d-block">Tipo de Evento</small>
                  <span className="badge bg-secondary-subtle text-secondary font-monospace">
                    {selectedLog.tipo}
                  </span>
                </div>
              </div>

              {/* Mensaje */}
              <div className="mt-3">
                <label className="form-label fw-bold small text-secondary">Mensaje / Resultado:</label>
                <div className="p-3 bg-light border rounded small">
                  {selectedLog.mensaje || "Sin mensaje descriptivo adicional."}
                </div>
              </div>

              {/* Traceback / Error Técnico si existe */}
              {selectedLog.error && (
                <div className="mt-3">
                  <div className="d-flex justify-content-between align-items-center mb-1">
                    <label className="form-label fw-bold small text-danger mb-0 d-flex align-items-center gap-1">
                      <AlertCircle size={14} /> Error Técnico / Traza de Excepción:
                    </label>
                    <button
                      className="btn btn-link btn-sm text-secondary p-0 d-flex align-items-center gap-1"
                      type="button"
                      onClick={() => copyToClipboard(selectedLog.error)}
                    >
                      <Copy size={13} /> Copiar error
                    </button>
                  </div>
                  <pre className="log-error-console p-3 rounded text-danger-emphasis bg-dark text-light font-monospace small">
                    {selectedLog.error}
                  </pre>
                </div>
              )}
            </div>

            <footer>
              {selectedLog.pedido_id && (
                <button
                  className="btn btn-outline-primary d-flex align-items-center gap-2"
                  type="button"
                  disabled={retrying}
                  onClick={() => handleRetry(selectedLog.pedido_id)}
                >
                  <RotateCcw size={16} className={retrying ? "animate-spin" : ""} />
                  {retrying ? "Reintentando..." : "Reintentar Notificaciones del Pedido"}
                </button>
              )}
              <button className="btn btn-light" type="button" onClick={() => setSelectedLog(null)}>
                Cerrar
              </button>
            </footer>
          </section>
        </div>
      )}
    </>
  );
}
