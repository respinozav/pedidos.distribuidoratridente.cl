import { useEffect, useState } from "react";
import {
  AlertCircle,
  Bot,
  Building,
  Calendar,
  Check,
  CheckCircle2,
  Clock,
  Copy,
  DollarSign,
  Eye,
  Mail,
  MessageCircle,
  Phone,
  RefreshCw,
  Search,
  Sparkles,
  X,
  XCircle,
} from "lucide-react";
import Swal from "sweetalert2";
import { api } from "../../services/api";
import StockAlertBell from "../../components/admin/StockAlertBell";

const dateFormatter = new Intl.DateTimeFormat("es-CL", {
  dateStyle: "short",
  timeStyle: "short",
});

const money = new Intl.NumberFormat("es-CL", {
  style: "currency",
  currency: "CLP",
});

const getLocalDateString = (d = new Date()) => {
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
};

const getLocalMonthStart = (d = new Date()) => {
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, "0");
  return `${year}-${month}-01`;
};

const today = getLocalDateString();
const monthStart = getLocalMonthStart();

export default function CamilaLogs() {
  const [logs, setLogs] = useState([]);
  const [stats, setStats] = useState({
    total: 0,
    con_whatsapp: 0,
    con_correo: 0,
    ambos_canales: 0,
    total_estimado_suma: 0,
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
  const [copiedField, setCopiedField] = useState("");

  async function loadStats() {
    try {
      const { data } = await api.get("/admin/camila/logs/stats");
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
      if (currentFilters.search && currentFilters.search.trim()) {
        params.search = currentFilters.search.trim();
      }
      if (currentFilters.desde) params.desde = currentFilters.desde;
      if (currentFilters.hasta) params.hasta = currentFilters.hasta;

      const { data } = await api.get("/admin/camila/logs", { params });
      setLogs(data.items);
      setTotal(data.total);
      setPage(data.page);
    } catch {
      Swal.fire({
        icon: "error",
        title: "Error al cargar logs de Camila",
        text: "No fue posible obtener el registro de conversaciones.",
      });
    } finally {
      setLoading(false);
      setInitialLoading(false);
    }
  }

  useEffect(() => {
    loadStats();
    loadLogs(1, filters);
  }, [filters.canal, filters.estado, filters.desde, filters.hasta]);

  function handleSearchSubmit(e) {
    e.preventDefault();
    loadLogs(1, filters);
  }

  function handleClearFilters() {
    const defaultFilters = {
      canal: "",
      estado: "",
      search: "",
      desde: monthStart,
      hasta: today,
    };
    setFilters(defaultFilters);
    loadLogs(1, defaultFilters);
  }

  function handleCopy(text, fieldName) {
    if (!text) return;
    navigator.clipboard.writeText(text);
    setCopiedField(fieldName);
    setTimeout(() => setCopiedField(""), 2000);
  }

  function renderStatusBadge(estado) {
    const st = (estado || "COMPLETADA").toUpperCase();
    if (st === "COMPLETADA" || st === "EXITOSO") {
      return (
        <span className="status-active d-inline-flex align-items-center gap-1">
          <CheckCircle2 size={12} /> Completada
        </span>
      );
    }
    if (st === "EN_PROCESO" || st === "PENDIENTE") {
      return (
        <span
          className="d-inline-flex align-items-center gap-1"
          style={{
            background: "#fef3c7",
            color: "#92400e",
            borderRadius: "99px",
            fontSize: "0.72rem",
            fontWeight: 750,
            padding: "0.3rem 0.55rem",
          }}
        >
          <Clock size={12} /> {st}
        </span>
      );
    }
    return (
      <span className="status-inactive d-inline-flex align-items-center gap-1">
        <XCircle size={12} /> {st}
      </span>
    );
  }

  const totalPages = Math.ceil(total / pageSize) || 1;

  return (
    <>
      <header className="admin-topbar">
        <div className="topbar-title">
          <p className="eyebrow mb-1">CONFIGURACION</p>
          <h1>Log Camila</h1>
        </div>
        <div className="topbar-actions">
          <span className="topbar-date d-none d-sm-inline">
            Ventas y Prospectos IA (www.distribuidoratridente.cl)
          </span>
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
          <StockAlertBell />
        </div>
      </header>

      <div className="admin-content dashboard-content">
        {/* Banner Hero */}
        <section className="dashboard-hero">
          <div>
            <p className="eyebrow d-flex align-items-center gap-1">
              <Sparkles size={14} color="#f59e0b" /> AGENTE VIRTUAL CAMILA
            </p>
            <h2>Conversaciones y Ventas Capturadas</h2>
            <p>
              Supervisa en tiempo real los clientes que contactan a Camila en{" "}
              <strong>www.distribuidoratridente.cl</strong>, sus datos de contacto y las alertas enviadas a administradores.
            </p>
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

        {/* Métricas Resumen */}
        <section className="dashboard-metrics log-metrics mb-4">
          <article>
            <span>TOTAL CONVERSACIONES</span>
            <strong>{stats.total}</strong>
            <small>Interacciones registradas</small>
          </article>
          <article>
            <span>CON WHATSAPP</span>
            <strong className="text-success">{stats.con_whatsapp}</strong>
            <small>Clientes con número móvil</small>
          </article>
          <article>
            <span>CON CORREO</span>
            <strong className="text-primary">{stats.con_correo}</strong>
            <small>Clientes con email registrado</small>
          </article>
          <article>
            <span>AMBOS CANALES</span>
            <strong style={{ color: "#7c3aed" }}>{stats.ambos_canales}</strong>
            <small>WhatsApp y Correo completos</small>
          </article>
        </section>

        {/* Panel Principal */}
        <section className="content-panel">
          <div className="panel-heading">
            <div>
              <h2>Listado de ventas y prospectos</h2>
              <p>Prioridad en Razón Social, WhatsApp y Correo capturados al finalizar la atención.</p>
            </div>
            <span className="panel-count">{total} registros</span>
          </div>

          {/* Filtros */}
          <form className="order-history-filters log-filters" onSubmit={handleSearchSubmit}>
            <label>
              Canal Notificado
              <select
                className="form-select"
                value={filters.canal}
                onChange={(e) => setFilters((curr) => ({ ...curr, canal: e.target.value }))}
              >
                <option value="">Todos los canales</option>
                <option value="WHATSAPP">WhatsApp</option>
                <option value="CORREO">Correo</option>
                <option value="AMBOS">Ambos (WSP + Correo)</option>
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
                <option value="COMPLETADA">Completada</option>
                <option value="EN_PROCESO">En proceso</option>
                <option value="ERROR">Error</option>
              </select>
            </label>

            <label style={{ flex: "1 1 240px" }}>
              Búsqueda
              <div className="d-flex gap-2">
                <input
                  className="form-control"
                  type="text"
                  placeholder="Razón Social, WhatsApp, Correo, producto..."
                  value={filters.search}
                  onChange={(e) => setFilters((curr) => ({ ...curr, search: e.target.value }))}
                />
                <button type="submit" className="btn btn-primary" title="Buscar">
                  <Search size={16} />
                </button>
                {(filters.search || filters.canal || filters.estado) && (
                  <button
                    type="button"
                    className="btn btn-outline-secondary"
                    onClick={handleClearFilters}
                    title="Limpiar filtros"
                  >
                    <X size={16} />
                  </button>
                )}
              </div>
            </label>
          </form>

          {/* Tabla */}
          {initialLoading ? (
            <p className="text-secondary p-4 mb-0">Cargando registros de Camila...</p>
          ) : logs.length === 0 ? (
            <div className="p-4 text-center text-secondary">
              <Bot size={40} className="mb-2 opacity-50" />
              <p className="mb-1 fw-bold">No se encontraron conversaciones de Camila.</p>
              <small>
                Asegúrate de que Camila en <strong>www.distribuidoratridente.cl</strong> esté registrando las ventas al finalizar.
              </small>
            </div>
          ) : (
            <div className="camila-log-table mt-3">
              <div className="camila-log-head">
                <span>Fecha / Hora</span>
                <span>Razón Social</span>
                <span>WhatsApp</span>
                <span>Correo</span>
                <span>Resumen Venta</span>
                <span>Notificado Admins</span>
                <span>Estado</span>
                <span>Detalle</span>
              </div>
              {logs.map((item) => (
                <div className="camila-log-row" key={item.id}>
                  <div>
                    <strong>{dateFormatter.format(new Date(item.created_at))}</strong>
                    <small className="text-muted">{item.origen || "WEB"}</small>
                  </div>
                  <div>
                    <strong className="d-flex align-items-center gap-1">
                      <Building size={14} className="text-secondary flex-shrink-0" />
                      <span className="text-truncate">{item.razon_social}</span>
                    </strong>
                    {item.total_estimado && (
                      <small className="text-success fw-bold">
                        Total: {money.format(item.total_estimado)}
                      </small>
                    )}
                  </div>
                  <div>
                    {item.whatsapp ? (
                      <a
                        href={`https://wa.me/${item.whatsapp.replace(/\D/g, "")}`}
                        target="_blank"
                        rel="noreferrer"
                        className="text-decoration-none d-inline-flex align-items-center gap-1 text-success fw-bold"
                        title="Abrir WhatsApp"
                      >
                        <MessageCircle size={14} />
                        <span>{item.whatsapp}</span>
                      </a>
                    ) : (
                      <span className="text-muted">-</span>
                    )}
                  </div>
                  <div>
                    {item.correo ? (
                      <a
                        href={`mailto:${item.correo}`}
                        className="text-decoration-none d-inline-flex align-items-center gap-1 text-primary text-truncate"
                        style={{ maxWidth: "160px" }}
                        title={item.correo}
                      >
                        <Mail size={14} className="flex-shrink-0" />
                        <span className="text-truncate">{item.correo}</span>
                      </a>
                    ) : (
                      <span className="text-muted">-</span>
                    )}
                  </div>
                  <div>
                    <span
                      className="d-block text-truncate"
                      style={{ maxWidth: "220px" }}
                      title={item.resumen || "Sin resumen"}
                    >
                      {item.resumen || "-"}
                    </span>
                  </div>
                  <div className="camila-channels">
                    {item.enviado_whatsapp && (
                      <span className="camila-badge camila-badge-wsp" title={item.destinatarios_whatsapp || "Enviado por WhatsApp"}>
                        WhatsApp
                      </span>
                    )}
                    {item.enviado_email && (
                      <span className="camila-badge camila-badge-mail" title={item.destinatarios_email || "Enviado por Correo"}>
                        Correo
                      </span>
                    )}
                    {!item.enviado_whatsapp && !item.enviado_email && (
                      <span className="status-inactive">No</span>
                    )}
                  </div>
                  <div>{renderStatusBadge(item.estado)}</div>
                  <button
                    className="icon-button"
                    onClick={() => setSelectedLog(item)}
                    aria-label="Ver conversación completa"
                    title="Ver conversación completa"
                  >
                    <Eye size={16} />
                  </button>
                </div>
              ))}
            </div>
          )}

          {/* Paginación */}
          {totalPages > 1 && (
            <div className="d-flex justify-content-between align-items-center mt-3 p-3 border-top">
              <span className="text-secondary small">
                Página {page} de {totalPages} ({total} registros)
              </span>
              <div className="d-flex gap-2">
                <button
                  className="btn btn-sm btn-outline-secondary"
                  disabled={page <= 1 || loading}
                  onClick={() => loadLogs(page - 1, filters)}
                >
                  Anterior
                </button>
                <button
                  className="btn btn-sm btn-outline-secondary"
                  disabled={page >= totalPages || loading}
                  onClick={() => loadLogs(page + 1, filters)}
                >
                  Siguiente
                </button>
              </div>
            </div>
          )}
        </section>
      </div>

      {/* Modal de Detalle de Conversación */}
      {selectedLog && (
        <div className="modal-backdrop-custom" onClick={() => setSelectedLog(null)}>
          <div
            className="category-modal"
            style={{ maxWidth: "720px", width: "95%" }}
            onClick={(e) => e.stopPropagation()}
          >
            <header>
              <div>
                <p className="eyebrow mb-1">DETALLE DE ATENCION - CAMILA</p>
                <h2>{selectedLog.razon_social}</h2>
              </div>
              <button
                type="button"
                className="icon-button"
                onClick={() => setSelectedLog(null)}
                aria-label="Cerrar detalle"
              >
                <X size={19} />
              </button>
            </header>

            <div className="modal-body-custom">
              {/* Resumen de Contacto */}
              <div
                style={{
                  background: "#f8fafc",
                  border: "1px solid #e2e8f0",
                  borderRadius: "8px",
                  padding: "1rem",
                  marginBottom: "1.25rem",
                }}
              >
                <h3 style={{ fontSize: "0.85rem", fontWeight: 800, color: "#1e293b", marginBottom: "0.75rem", textTransform: "uppercase" }}>
                  Datos Principales del Prospecto
                </h3>
                <div className="row g-3">
                  <div className="col-12 col-md-6">
                    <label className="text-muted small d-block mb-1">Razón Social</label>
                    <div className="d-flex align-items-center justify-content-between bg-white p-2 rounded border">
                      <strong className="text-truncate">{selectedLog.razon_social}</strong>
                      <button
                        className="btn btn-link btn-sm p-0 text-secondary"
                        onClick={() => handleCopy(selectedLog.razon_social, "razon")}
                        title="Copiar"
                      >
                        {copiedField === "razon" ? <Check size={14} className="text-success" /> : <Copy size={14} />}
                      </button>
                    </div>
                  </div>
                  <div className="col-12 col-md-6">
                    <label className="text-muted small d-block mb-1">WhatsApp</label>
                    <div className="d-flex align-items-center justify-content-between bg-white p-2 rounded border">
                      {selectedLog.whatsapp ? (
                        <a
                          href={`https://wa.me/${selectedLog.whatsapp.replace(/\D/g, "")}`}
                          target="_blank"
                          rel="noreferrer"
                          className="text-success fw-bold text-decoration-none d-flex align-items-center gap-1"
                        >
                          <MessageCircle size={14} /> {selectedLog.whatsapp}
                        </a>
                      ) : (
                        <span className="text-muted">No informado</span>
                      )}
                      {selectedLog.whatsapp && (
                        <button
                          className="btn btn-link btn-sm p-0 text-secondary"
                          onClick={() => handleCopy(selectedLog.whatsapp, "wsp")}
                          title="Copiar WhatsApp"
                        >
                          {copiedField === "wsp" ? <Check size={14} className="text-success" /> : <Copy size={14} />}
                        </button>
                      )}
                    </div>
                  </div>
                  <div className="col-12 col-md-6">
                    <label className="text-muted small d-block mb-1">Correo Electrónico</label>
                    <div className="d-flex align-items-center justify-content-between bg-white p-2 rounded border">
                      {selectedLog.correo ? (
                        <a
                          href={`mailto:${selectedLog.correo}`}
                          className="text-primary text-decoration-none d-flex align-items-center gap-1 text-truncate"
                        >
                          <Mail size={14} /> {selectedLog.correo}
                        </a>
                      ) : (
                        <span className="text-muted">No informado</span>
                      )}
                      {selectedLog.correo && (
                        <button
                          className="btn btn-link btn-sm p-0 text-secondary"
                          onClick={() => handleCopy(selectedLog.correo, "mail")}
                          title="Copiar correo"
                        >
                          {copiedField === "mail" ? <Check size={14} className="text-success" /> : <Copy size={14} />}
                        </button>
                      )}
                    </div>
                  </div>
                  <div className="col-12 col-md-6">
                    <label className="text-muted small d-block mb-1">Fecha de Atención</label>
                    <div className="bg-white p-2 rounded border">
                      <span>{dateFormatter.format(new Date(selectedLog.created_at))}</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Alertas enviadas a administradores */}
              <div
                style={{
                  background: "#f0fdf4",
                  border: "1px solid #bbf7d0",
                  borderRadius: "8px",
                  padding: "1rem",
                  marginBottom: "1.25rem",
                }}
              >
                <h3 style={{ fontSize: "0.85rem", fontWeight: 800, color: "#166534", marginBottom: "0.5rem", textTransform: "uppercase" }}>
                  Notificaciones Despachadas
                </h3>
                <div className="d-flex flex-column gap-2 small">
                  <div>
                    <strong>WhatsApp a Admins: </strong>
                    {selectedLog.enviado_whatsapp ? (
                      <span className="text-success fw-bold">
                        Enviado {selectedLog.destinatarios_whatsapp ? `(${selectedLog.destinatarios_whatsapp})` : ""}
                      </span>
                    ) : (
                      <span className="text-muted">No enviado</span>
                    )}
                  </div>
                  <div>
                    <strong>Correo a Admins: </strong>
                    {selectedLog.enviado_email ? (
                      <span className="text-primary fw-bold">
                        Enviado {selectedLog.destinatarios_email ? `(${selectedLog.destinatarios_email})` : ""}
                      </span>
                    ) : (
                      <span className="text-muted">No enviado</span>
                    )}
                  </div>
                </div>
              </div>

              {/* Resumen de Venta */}
              {selectedLog.resumen && (
                <div className="mb-3">
                  <label className="form-label fw-bold">Resumen de Venta / Pedido</label>
                  <div
                    style={{
                      background: "#fff",
                      border: "1px solid #cbd5e1",
                      borderRadius: "6px",
                      padding: "0.75rem",
                      whiteSpace: "pre-wrap",
                      fontSize: "0.85rem",
                    }}
                  >
                    {selectedLog.resumen}
                  </div>
                </div>
              )}

              {/* Transcripción de la Conversación */}
              <div className="mb-3">
                <div className="d-flex justify-content-between align-items-center mb-1">
                  <label className="form-label fw-bold mb-0">Conversación Completa con Camila</label>
                  {selectedLog.conversacion && (
                    <button
                      className="btn btn-outline-secondary btn-sm d-flex align-items-center gap-1 py-1"
                      onClick={() => handleCopy(selectedLog.conversacion, "chat")}
                    >
                      {copiedField === "chat" ? <Check size={14} className="text-success" /> : <Copy size={14} />}
                      <span>{copiedField === "chat" ? "Copiado" : "Copiar Chat"}</span>
                    </button>
                  )}
                </div>
                <div
                  style={{
                    background: "#0f172a",
                    color: "#e2e8f0",
                    borderRadius: "6px",
                    padding: "1rem",
                    maxHeight: "320px",
                    overflowY: "auto",
                    fontFamily: "monospace",
                    fontSize: "0.82rem",
                    whiteSpace: "pre-wrap",
                    lineHeight: "1.5",
                  }}
                >
                  {selectedLog.conversacion || "No hay texto de conversación registrado."}
                </div>
              </div>
            </div>

            <footer>
              <button className="btn btn-primary" type="button" onClick={() => setSelectedLog(null)}>
                Cerrar
              </button>
            </footer>
          </div>
        </div>
      )}
    </>
  );
}
