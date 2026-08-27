import { useEffect, useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  Clock,
  Copy,
  Eye,
  Globe,
  KeyRound,
  Laptop,
  RefreshCw,
  Search,
  ShieldAlert,
  ShieldCheck,
  User,
  UserCheck,
  Users,
  X,
  XCircle,
} from "lucide-react";
import Swal from "sweetalert2";
import { api } from "../../services/api";

const dateFormatter = new Intl.DateTimeFormat("es-CL", {
  dateStyle: "short",
  timeStyle: "short",
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

export default function SessionLogs() {
  const [logs, setLogs] = useState([]);
  const [stats, setStats] = useState({
    total: 0,
    exitosos: 0,
    fallidos: 0,
    admin_total: 0,
    cliente_total: 0,
  });
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const pageSize = 20;

  const [filters, setFilters] = useState({
    tipo_usuario: "",
    estado: "",
    search: "",
    desde: monthStart,
    hasta: today,
  });

  const [initialLoading, setInitialLoading] = useState(true);
  const [loading, setLoading] = useState(false);
  const [selectedLog, setSelectedLog] = useState(null);

  async function loadStats() {
    try {
      const { data } = await api.get("/admin/sesiones/logs/stats");
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
      if (currentFilters.tipo_usuario) params.tipo_usuario = currentFilters.tipo_usuario;
      if (currentFilters.estado) params.estado = currentFilters.estado;
      if (currentFilters.search && currentFilters.search.trim()) params.search = currentFilters.search.trim();
      if (currentFilters.desde) params.desde = currentFilters.desde;
      if (currentFilters.hasta) params.hasta = currentFilters.hasta;

      const { data } = await api.get("/admin/sesiones/logs", { params });
      setLogs(data.items);
      setTotal(data.total);
      setPage(data.page);
    } catch {
      Swal.fire({
        icon: "error",
        title: "Error al cargar logs de sesión",
        text: "No fue posible obtener el registro de auditoría de sesiones.",
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
  }, [filters.tipo_usuario, filters.estado, filters.search, filters.desde, filters.hasta]);

  function copyToClipboard(text, label = "Copiado al portapapeles") {
    if (!text) return;
    navigator.clipboard.writeText(text);
    Swal.fire({
      toast: true,
      position: "top-end",
      icon: "success",
      title: label,
      showConfirmButton: false,
      timer: 1500,
    });
  }

  function renderUserTypeBadge(tipo) {
    if (tipo === "ADMINISTRADOR") {
      return (
        <span className="badge-channel badge-email-admin">
          <ShieldCheck size={13} /> Admin
        </span>
      );
    }
    return (
      <span className="badge-channel badge-email-client">
        <UserCheck size={13} /> Cliente
      </span>
    );
  }

  function renderStatusBadge(estado) {
    if (estado === "EXITOSO") {
      return (
        <span className="status-active d-inline-flex align-items-center gap-1">
          <CheckCircle2 size={13} /> Exitoso
        </span>
      );
    }
    return (
      <span className="status-inactive d-inline-flex align-items-center gap-1">
        <XCircle size={13} /> Fallido
      </span>
    );
  }

  const totalPages = Math.ceil(total / pageSize) || 1;

  return (
    <>
      <header className="admin-topbar">
        <div className="topbar-title">
          <p className="eyebrow mb-1">CONFIGURACION</p>
          <h1>Logs de Sesiones</h1>
        </div>
        <div className="topbar-actions">
          <span className="topbar-date d-none d-sm-inline">Auditoría de Inicios de Sesión</span>
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
        {/* Banner Hero Superior */}
        <section className="dashboard-hero">
          <div>
            <p className="eyebrow">SEGURIDAD & AUDITORIA</p>
            <h2>Registro de Accesos e Intentos de Inicio de Sesión</h2>
            <p>Supervisa todos los accesos exitosos y bloqueos por credenciales incorrectas o cuentas inactivas.</p>
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
        <section className="dashboard-metrics log-metrics mb-4">
          <article>
            <span>TOTAL INTENTOS</span>
            <strong>{stats.total}</strong>
            <small>Inicios registrados</small>
          </article>
          <article>
            <span>INICIOS EXITOSOS</span>
            <strong className="text-success">{stats.exitosos}</strong>
            <small>Autenticaciones correctas</small>
          </article>
          <article>
            <span>INICIOS FALLIDOS</span>
            <strong className={stats.fallidos > 0 ? "text-danger" : ""}>{stats.fallidos}</strong>
            <small>
              {stats.fallidos > 0 ? (
                <span className="text-danger fw-bold">Intentos rechazados</span>
              ) : (
                "0 rechazados"
              )}
            </small>
          </article>
          <article>
            <span>CLIENTES / ADMINS</span>
            <strong>
              {stats.cliente_total} <span className="text-secondary fw-normal fs-6">/</span> {stats.admin_total}
            </strong>
            <small>Clientes vs Administradores</small>
          </article>
        </section>

        {/* Panel Principal */}
        <section className="content-panel">
          <div className="panel-heading">
            <div>
              <h2>Listado de sesiones</h2>
              <p>Filtra por tipo de usuario, estado o busca por correo/nombre/IP.</p>
            </div>
            <span className="panel-count">{total} registros</span>
          </div>

          {/* Filtros */}
          <div className="order-history-filters log-filters">
            <label>
              Tipo de Usuario
              <select
                className="form-select"
                value={filters.tipo_usuario}
                onChange={(e) => setFilters((curr) => ({ ...curr, tipo_usuario: e.target.value }))}
              >
                <option value="">Todos</option>
                <option value="ADMINISTRADOR">Administrador</option>
                <option value="CLIENTE">Cliente</option>
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
                <option value="EXITOSO">Exitoso</option>
                <option value="FALLIDO">Fallido</option>
              </select>
            </label>

            <label>
              Buscar
              <input
                className="form-control"
                type="search"
                placeholder="Ej. correo, nombre o IP..."
                value={filters.search}
                onChange={(e) => setFilters((curr) => ({ ...curr, search: e.target.value }))}
              />
            </label>
          </div>

          {/* Grilla / Tabla */}
          {initialLoading ? (
            <p className="mt-4 text-secondary">Cargando registros de auditoría de sesiones...</p>
          ) : logs.length ? (
            <>
              <div className="admin-log-table mt-4">
                <div className="admin-log-head" style={{ gridTemplateColumns: "1.2fr 0.9fr 1.5fr 0.9fr 1.5fr 1fr 0.5fr" }}>
                  <span>Fecha y Hora</span>
                  <span>Tipo</span>
                  <span>Usuario / Correo</span>
                  <span>Estado</span>
                  <span>Motivo</span>
                  <span>Dirección IP</span>
                  <span className="text-center">Acciones</span>
                </div>
                {logs.map((log) => (
                  <article
                    className="admin-log-row"
                    key={log.id}
                    style={{ gridTemplateColumns: "1.2fr 0.9fr 1.5fr 0.9fr 1.5fr 1fr 0.5fr" }}
                  >
                    <span>{log.created_at ? dateFormatter.format(new Date(log.created_at)) : "-"}</span>
                    <div>{renderUserTypeBadge(log.tipo_usuario)}</div>
                    <div>
                      <div className="fw-semibold text-truncate" title={log.nombre || log.correo}>
                        {log.nombre || "Desconocido"}
                      </div>
                      <small className="text-secondary d-block text-truncate" title={log.correo}>
                        {log.correo}
                      </small>
                    </div>
                    <div>{renderStatusBadge(log.estado)}</div>
                    <span className="small text-truncate" title={log.mensaje || "-"}>
                      {log.mensaje || "-"}
                    </span>
                    <span className="font-monospace small text-truncate" title={log.ip_address || "N/D"}>
                      {log.ip_address || "N/D"}
                    </span>
                    <div className="text-center">
                      <button
                        className="icon-button category-edit"
                        type="button"
                        onClick={() => setSelectedLog(log)}
                        aria-label="Ver detalle del log"
                        title="Ver detalle completo"
                      >
                        <Eye size={16} />
                      </button>
                    </div>
                  </article>
                ))}
              </div>

              {/* Paginación */}
              <nav className="product-pagination mt-4" aria-label="Paginación de logs">
                <small>
                  Página {page} de {totalPages} · {total} registros
                </small>
                <button
                  className="btn btn-outline-primary btn-sm"
                  type="button"
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
                  className="btn btn-primary btn-sm"
                  type="button"
                  disabled={page >= totalPages}
                  onClick={() => {
                    const newPage = page + 1;
                    setPage(newPage);
                    loadLogs(newPage, filters);
                  }}
                >
                  Siguiente
                </button>
              </nav>
            </>
          ) : (
            <p className="history-filter-empty">No hay registros de inicio de sesión que coincidan con los filtros.</p>
          )}
        </section>
      </div>

      {/* Modal de Detalle del Log */}
      {selectedLog && (
        <div className="modal-backdrop-custom">
          <section className="category-modal log-detail-modal" role="dialog" aria-modal="true" style={{ maxWidth: "600px" }}>
            <header>
              <div>
                <p className="eyebrow">DETALLE DE AUDITORIA</p>
                <h2>Registro de Inicio de Sesión</h2>
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
                  <small className="text-muted d-block">Tipo de Usuario</small>
                  {renderUserTypeBadge(selectedLog.tipo_usuario)}
                </div>
                <div>
                  <small className="text-muted d-block">Resultado / Estado</small>
                  {renderStatusBadge(selectedLog.estado)}
                </div>
                <div>
                  <small className="text-muted d-block">Correo Ingresado</small>
                  <strong>{selectedLog.correo}</strong>
                </div>
                <div>
                  <small className="text-muted d-block">Nombre Resuelto</small>
                  <span>{selectedLog.nombre || "No resuelto / No existe"}</span>
                </div>
                <div>
                  <small className="text-muted d-block">Dirección IP</small>
                  <span className="font-monospace d-flex align-items-center gap-1">
                    <Globe size={14} className="text-secondary" />
                    {selectedLog.ip_address || "No detectada"}
                  </span>
                </div>
                <div>
                  <small className="text-muted d-block">Identificador Vinculado</small>
                  <span className="font-monospace small">
                    {selectedLog.usuario_id
                      ? `Usuario: ${selectedLog.usuario_id.slice(0, 8)}...`
                      : selectedLog.cliente_id
                      ? `Cliente: ${selectedLog.cliente_id.slice(0, 8)}...`
                      : "Sin vínculo"}
                  </span>
                </div>
              </div>

              {/* Mensaje / Resultado */}
              <div className="mt-3">
                <label className="form-label fw-bold small text-secondary">Motivo / Mensaje:</label>
                <div
                  className={`p-3 rounded small border ${
                    selectedLog.estado === "EXITOSO"
                      ? "bg-success-subtle border-success-subtle text-success-emphasis"
                      : "bg-danger-subtle border-danger-subtle text-danger-emphasis"
                  }`}
                >
                  {selectedLog.mensaje || "Sin detalle descriptivo."}
                </div>
              </div>

              {/* User Agent / Dispositivo */}
              <div className="mt-3">
                <div className="d-flex justify-content-between align-items-center mb-1">
                  <label className="form-label fw-bold small text-secondary mb-0 d-flex align-items-center gap-1">
                    <Laptop size={14} /> Dispositivo y Navegador (User-Agent):
                  </label>
                  {selectedLog.user_agent && (
                    <button
                      className="btn btn-link btn-sm text-secondary p-0 d-flex align-items-center gap-1"
                      type="button"
                      onClick={() => copyToClipboard(selectedLog.user_agent, "User-Agent copiado")}
                    >
                      <Copy size={13} /> Copiar
                    </button>
                  )}
                </div>
                <div className="p-3 bg-dark text-light rounded font-monospace small" style={{ wordBreak: "break-all", whiteSpace: "pre-wrap" }}>
                  {selectedLog.user_agent || "No informado"}
                </div>
              </div>
            </div>

            <footer>
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
