import { useEffect, useState } from "react";
import {
  AlertCircle,
  Clock,
  Copy,
  Eye,
  Mail,
  MessageSquare,
  RefreshCw,
  RotateCcw,
  X,
} from "lucide-react";
import Swal from "sweetalert2";
import { api } from "../../services/api";

const dateFormatter = new Intl.DateTimeFormat("es-CL", {
  dateStyle: "short",
  timeStyle: "short",
});

const today = new Date().toISOString().slice(0, 10);
const monthStart = `${today.slice(0, 7)}-01`;

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
    desde: monthStart,
    hasta: today,
  });

  const [initialLoading, setInitialLoading] = useState(true);
  const [loading, setLoading] = useState(false);
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

  async function loadLogs(targetPage = page, currentFilters = filters) {
    setLoading(true);
    try {
      const params = {
        page: targetPage,
        page_size: pageSize,
      };
      if (currentFilters.canal) params.canal = currentFilters.canal;
      if (currentFilters.estado) params.estado = currentFilters.estado;
      if (currentFilters.search && currentFilters.search.trim()) params.search = currentFilters.search.trim();
      if (currentFilters.desde) params.desde = currentFilters.desde;
      if (currentFilters.hasta) params.hasta = currentFilters.hasta;

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
      setInitialLoading(false);
    }
  }

  useEffect(() => {
    loadStats();
    const timer = setTimeout(() => {
      loadLogs(1, filters);
    }, 250);
    return () => clearTimeout(timer);
  }, [filters.canal, filters.estado, filters.search, filters.desde, filters.hasta]);

  async function handleRetry(orderId) {
    if (!orderId || retrying) return;

    const confirmResult = await Swal.fire({
      title: "¿Reenviar notificaciones?",
      text: "Se generará nuevamente el PDF y se reenviarán los avisos por WhatsApp y correo. Evita hacer reenvíos seguidos para prevenir que WhatsApp o el servidor de correos bloqueen los mensajes por spam.",
      icon: "question",
      showCancelButton: true,
      confirmButtonColor: "#0f766e",
      cancelButtonColor: "#64748b",
      confirmButtonText: "Sí, reenviar ahora",
      cancelButtonText: "Cancelar",
    });

    if (!confirmResult.isConfirmed) return;

    setRetrying(true);
    try {
      await api.post(`/admin/pedidos/${orderId}/reintentar-notificaciones`);
      Swal.fire({
        icon: "success",
        title: "Reintento en curso",
        text: "Las notificaciones se están procesando en segundo plano.",
        timer: 2500,
        showConfirmButton: false,
      });
      setTimeout(() => {
        loadStats();
        loadLogs(page, filters);
      }, 2000);
    } catch (err) {
      const isRateLimit = err.response?.status === 429;
      Swal.fire({
        icon: isRateLimit ? "warning" : "error",
        title: isRateLimit ? "Límite de reenvío alcanzado" : "No fue posible reintentar",
        text: err.response?.data?.detail ?? "Ocurrió un error al solicitar el reintento.",
      });
    } finally {
      setTimeout(() => setRetrying(false), 3000);
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
          <MessageSquare size={13} /> WhatsApp
        </span>
      );
    }
    if (canal === "EMAIL_ADMIN") {
      return (
        <span className="badge-channel badge-email-admin">
          <Mail size={13} /> Correo Admin
        </span>
      );
    }
    if (canal === "EMAIL_CLIENTE") {
      return (
        <span className="badge-channel badge-email-client">
          <Mail size={13} /> Correo Cliente
        </span>
      );
    }
    return (
      <span className="badge-channel badge-system">
        Sistema
      </span>
    );
  }

  function renderStatusBadge(estado) {
    if (estado === "ENVIADO") {
      return <span className="status-active">Enviado</span>;
    }
    if (estado === "FALLIDO") {
      return <span className="status-inactive">Fallido</span>;
    }
    return <span className="status-skipped">Omitido</span>;
  }

  const totalPages = Math.ceil(total / pageSize) || 1;

  return (
    <>
      <header className="admin-topbar">
        <div className="topbar-title">
          <p className="eyebrow mb-1">CONFIGURACION</p>
          <h1>Logs de Envíos</h1>
        </div>
        <div className="topbar-actions">
          <span className="topbar-date d-none d-sm-inline">Auditoría de Notificaciones</span>
          <button
            className="btn btn-outline-secondary d-flex align-items-center gap-2"
            onClick={() => {
              loadStats();
              loadLogs(page, filters);
            }}
            disabled={loading}
          >
            <RefreshCw size={16} className={loading ? "animate-spin" : ""} />
            <span>Actualizar</span>
          </button>
        </div>
      </header>

      <div className="admin-content dashboard-content">
        {/* Banner Hero Azul Superior */}
        <section className="dashboard-hero">
          <div>
            <p className="eyebrow">NOTIFICACIONES</p>
            <h2>Historial y Auditoría de Notificaciones</h2>
            <p>Revisa el estado de entrega en tiempo real de cada WhatsApp y correo electrónico.</p>
          </div>
          <div className="dashboard-date-filters">
            <label>
              Desde
              <input
                className="form-control"
                type="date"
                value={filters.desde}
                max={filters.hasta || undefined}
                onChange={(e) => setFilters((curr) => ({ ...curr, desde: e.target.value }))}
              />
            </label>
            <label>
              Hasta
              <input
                className="form-control"
                type="date"
                value={filters.hasta}
                min={filters.desde || undefined}
                max={today}
                onChange={(e) => setFilters((curr) => ({ ...curr, hasta: e.target.value }))}
              />
            </label>
          </div>
        </section>

        {/* Tarjetas de Métricas Resumen */}
        <section className="dashboard-metrics mb-4">
          <article>
            <span>TOTAL EVENTOS</span>
            <strong>{stats.total}</strong>
            <small>Auditorías registradas</small>
          </article>
          <article>
            <span>WHATSAPP ENVIADOS</span>
            <strong>{stats.whatsapp_enviados}</strong>
            <small>
              {stats.whatsapp_fallidos > 0 ? (
                <span className="text-danger fw-bold">{stats.whatsapp_fallidos} fallidos</span>
              ) : (
                "0 fallidos"
              )}
            </small>
          </article>
          <article>
            <span>CORREOS ENVIADOS</span>
            <strong>{stats.email_enviados}</strong>
            <small>
              {stats.email_fallidos > 0 ? (
                <span className="text-danger fw-bold">{stats.email_fallidos} fallidos</span>
              ) : (
                "0 fallidos"
              )}
            </small>
          </article>
          <article>
            <span>NOTIFICACIONES OMITIDAS</span>
            <strong>{stats.omitidos}</strong>
            <small>Sin teléfono o config</small>
          </article>
        </section>

        {/* Panel Principal */}
        <section className="content-panel">
          <div className="panel-heading">
            <div>
              <h2>Listado de registros</h2>
              <p>Filtra por canal, estado o código de pedido.</p>
            </div>
            <span className="panel-count">{total} registros</span>
          </div>

          {/* Filtros Alineados Sin Botón Buscar ni Limpiar */}
          <div className="order-history-filters log-filters">
            <label>
              Canal
              <select
                className="form-select"
                value={filters.canal}
                onChange={(e) => setFilters((curr) => ({ ...curr, canal: e.target.value }))}
              >
                <option value="">Todos</option>
                <option value="WHATSAPP">WhatsApp</option>
                <option value="EMAIL_ADMIN">Correo Admin</option>
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
                <option value="">Todos</option>
                <option value="ENVIADO">Enviado</option>
                <option value="FALLIDO">Fallido</option>
                <option value="OMITIDO">Omitido</option>
              </select>
            </label>

            <label>
              Pedido
              <input
                className="form-control"
                type="search"
                placeholder="Ej. 4CB969B1 o destinatario"
                value={filters.search}
                onChange={(e) => setFilters((curr) => ({ ...curr, search: e.target.value }))}
              />
            </label>
          </div>

          {/* Grilla / Tabla con el mismo modelo de Pedidos y Productos */}
          {initialLoading ? (
            <p className="mt-4 text-secondary">Cargando registros de auditoría...</p>
          ) : logs.length ? (
            <>
              <div className="admin-log-table mt-4">
                <div className="admin-log-head">
                  <span>Número de pedido</span>
                  <span>Fecha</span>
                  <span>Canal</span>
                  <span>Estado</span>
                  <span>Duración</span>
                  <span>Acciones</span>
                </div>
                {logs.map((log) => (
                  <article className="admin-log-row" key={log.id}>
                    <strong>
                      {log.pedido_id ? `Pedido ${log.pedido_id.slice(0, 8).toUpperCase()}` : "Sin pedido"}
                    </strong>
                    <span>{log.created_at ? dateFormatter.format(new Date(log.created_at)) : "-"}</span>
                    <div>{renderChannelBadge(log.canal)}</div>
                    <div>{renderStatusBadge(log.estado)}</div>
                    <strong className="font-monospace text-secondary">
                      {log.duracion_ms != null
                        ? log.duracion_ms >= 1000
                          ? `${(log.duracion_ms / 1000).toFixed(2)}s`
                          : `${log.duracion_ms}ms`
                        : "-"}
                    </strong>
                    <button
                      className="icon-button category-edit"
                      type="button"
                      onClick={() => setSelectedLog(log)}
                      aria-label="Ver detalle del log"
                      title="Ver detalle completo"
                    >
                      <Eye size={16} />
                    </button>
                  </article>
                ))}
              </div>

              {/* Paginación */}
              <div className="product-pagination mt-4">
                <small>
                  Página {page} de {totalPages} ({total} registros)
                </small>
                <div className="d-flex gap-2">
                  <button
                    className="btn btn-outline-secondary btn-sm"
                    disabled={page <= 1}
                    onClick={() => {
                      const newPage = page - 1;
                      setPage(newPage);
                      loadLogs(newPage, filters);
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
                      loadLogs(newPage, filters);
                    }}
                  >
                    Siguiente
                  </button>
                </div>
              </div>
            </>
          ) : (
            <p className="history-filter-empty">No hay registros que coincidan con los filtros.</p>
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
                      Pedido {selectedLog.pedido_id.slice(0, 8).toUpperCase()}
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
