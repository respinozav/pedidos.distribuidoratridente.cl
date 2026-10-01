import React, { useEffect, useMemo, useState } from "react";
import {
  Calendar,
  CheckCircle2,
  ChevronRight,
  DollarSign,
  Download,
  Eye,
  Filter,
  Package,
  RotateCcw,
  Search,
  ShoppingBag,
  TrendingUp,
  User,
  Users,
  X,
} from "lucide-react";
import { api } from "../../services/api";
import { formatDateTime } from "../../main";
import StockAlertBell from "../../components/admin/StockAlertBell";

const money = new Intl.NumberFormat("es-CL", { style: "currency", currency: "CLP" });

function getDefaultDates() {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return {
    monthStart: `${year}-${month}-01`,
    today: `${year}-${month}-${day}`,
  };
}

export default function AdminVentasManager() {
  const { monthStart, today } = useMemo(() => getDefaultDates(), []);
  const [data, setData] = useState({
    total_ventas: 0,
    total_comisiones: 0,
    cantidad_pedidos: 0,
    vendedores_activos: 0,
    vendedores_resumen: [],
    vendedores_disponibles: [],
    items: [],
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Filtros
  const [desde, setDesde] = useState(monthStart);
  const [hasta, setHasta] = useState(today);
  const [selectedVendedorId, setSelectedVendedorId] = useState("");
  const [search, setSearch] = useState("");

  // Modal detalle
  const [selectedVenta, setSelectedVenta] = useState(null);

  async function loadVentas() {
    setLoading(true);
    setError("");
    try {
      const params = {};
      if (desde) params.desde = desde;
      if (hasta) params.hasta = hasta;
      if (selectedVendedorId) params.vendedor_id = selectedVendedorId;

      const res = await api.get("/admin/ventas", { params });
      setData(res.data);
    } catch {
      setError("No fue posible cargar las ventas de vendedores. Intenta nuevamente.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadVentas();
  }, [desde, hasta, selectedVendedorId]);

  // Filtrado de pedidos por texto (cliente, RUT o código de pedido)
  const filteredItems = useMemo(() => {
    let result = data.items;
    const q = search.trim().toLowerCase();
    if (q) {
      result = result.filter((item) => {
        const clienteNombre = (item.cliente?.nombre || "").toLowerCase();
        const clienteRut = (item.cliente?.rut || "").toLowerCase();
        const vendedorNombre = (item.vendedor?.nombre || "").toLowerCase();
        const pedidoId = (item.pedido_id || "").toLowerCase();
        return (
          clienteNombre.includes(q) ||
          clienteRut.includes(q) ||
          vendedorNombre.includes(q) ||
          pedidoId.includes(q)
        );
      });
    }
    return result;
  }, [data.items, search]);

  const hasActiveFilters =
    desde !== monthStart || hasta !== today || Boolean(selectedVendedorId) || Boolean(search);

  const selectedVendedorName = useMemo(() => {
    if (!selectedVendedorId) return null;
    const v = data.vendedores_disponibles.find((item) => String(item.id) === String(selectedVendedorId));
    if (v) return v.nombre;
    const fromSummary = data.vendedores_resumen.find((item) => String(item.vendedor_id) === String(selectedVendedorId));
    return fromSummary ? fromSummary.nombre : null;
  }, [selectedVendedorId, data.vendedores_disponibles, data.vendedores_resumen]);

  const handleVerPedidosVendedor = (vendedorId) => {
    setSelectedVendedorId(String(vendedorId));
    setTimeout(() => {
      const el = document.getElementById("pedidos-realizados-section");
      if (el) {
        el.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    }, 50);
  };

  return (
    <>
      <header className="admin-topbar">
        <div className="topbar-title">
          <p className="eyebrow mb-1">GESTION COMERCIAL</p>
          <h1>Ventas y Comisiones</h1>
        </div>
        <div className="topbar-actions">
          <span className="topbar-date d-none d-sm-inline">Fuerza de Venta</span>
          <StockAlertBell />
        </div>
      </header>

      <div className="admin-content dashboard-content">
        {/* Banner de resumen (Hero sin filtros apiñados) */}
        <section className="dashboard-hero mb-3">
          <div>
            <p className="eyebrow">FUERZA DE VENTA</p>
            <h2>Comisiones y Pedidos por Vendedor</h2>
            <p>
              Supervisa las ventas acumuladas por cada vendedor, revisa sus comisiones y consulta el detalle de los pedidos.
            </p>
          </div>
        </section>

        {/* 1. Tarjetas métricas nativas del sistema (ARRIBA) */}
        <section className="dashboard-metrics">
          <article>
            <span>VENTAS TOTALES</span>
            <strong>{money.format(data.total_ventas)}</strong>
            <small>
              {data.cantidad_pedidos} {data.cantidad_pedidos === 1 ? "pedido registrado" : "pedidos registrados"}
            </small>
          </article>
          <article style={{ "--metric-color": "#15803d", background: "#e9f8ee" }}>
            <span>COMISIONES TOTALES</span>
            <strong style={{ color: "#15803d" }}>{money.format(data.total_comisiones)}</strong>
            <small style={{ color: "#166534" }}>Generadas en el periodo</small>
          </article>
          <article>
            <span>TOTAL PEDIDOS</span>
            <strong>{data.cantidad_pedidos}</strong>
            <small>
              {selectedVendedorName ? `De ${selectedVendedorName}` : "Por vendedores"}
            </small>
          </article>
          <article>
            <span>VENDEDORES ACTIVOS</span>
            <strong>{data.vendedores_activos}</strong>
            <small>De {data.vendedores_disponibles.length} registrados</small>
          </article>
        </section>

        {/* 2. Filtro de Vendedor y Fechas (DEBAJO DE LAS CARDS, siguiendo el patrón de los demás estilos) */}
        <div className="admin-order-filters vendor-sales-filters mb-4">
          <label className="filter-desde">
            Desde
            <input
              className="form-control"
              type="date"
              value={desde}
              max={hasta || today}
              onChange={(e) => setDesde(e.target.value)}
            />
          </label>

          <label className="filter-hasta">
            Hasta
            <input
              className="form-control"
              type="date"
              value={hasta}
              min={desde || undefined}
              max={today}
              onChange={(e) => setHasta(e.target.value)}
            />
          </label>

          <label className="filter-vendedor" style={{ minWidth: "220px" }}>
            Vendedor
            <select
              className="form-select"
              value={selectedVendedorId}
              onChange={(e) => setSelectedVendedorId(e.target.value)}
            >
              <option value="">Todos los vendedores</option>
              {data.vendedores_disponibles.map((vend) => (
                <option key={vend.id} value={vend.id}>
                  {vend.nombre}
                </option>
              ))}
            </select>
          </label>

          <label className="filter-cliente">
            Buscar
            <input
              className="form-control"
              type="search"
              placeholder="Cliente, RUT o código de pedido..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </label>

          {hasActiveFilters && (
            <div className="d-flex align-items-end">
              <button
                type="button"
                className="btn btn-outline-secondary"
                style={{ minHeight: "38px", whiteSpace: "nowrap" }}
                onClick={() => {
                  setDesde(monthStart);
                  setHasta(today);
                  setSelectedVendedorId("");
                  setSearch("");
                }}
                title="Restablecer filtros"
              >
                <RotateCcw size={15} className="me-1" />
                <span>Restablecer</span>
              </button>
            </div>
          )}
        </div>

        {error && <div className="alert alert-danger mb-4">{error}</div>}

        {/* 3. Panel: Comisiones por Vendedor */}
        <section className="content-panel mb-4">
          <div className="panel-heading">
            <div>
              <h2>Comisiones por Vendedor</h2>
              <p>Consolidado de ventas y comisiones generadas en el periodo seleccionado.</p>
            </div>
            <div className="d-flex align-items-center gap-2">
              {selectedVendedorId && (
                <button
                  type="button"
                  className="btn btn-outline-primary btn-sm"
                  onClick={() => setSelectedVendedorId("")}
                >
                  Ver todos los vendedores
                </button>
              )}
              <span className="panel-count">
                {data.vendedores_resumen.length}{" "}
                {data.vendedores_resumen.length === 1 ? "vendedor con ventas" : "vendedores con ventas"}
              </span>
            </div>
          </div>

          {loading ? (
            <p className="mt-3 text-secondary">Cargando resumen de comisiones...</p>
          ) : data.vendedores_resumen.length === 0 ? (
            <p className="history-filter-empty py-4 text-center">
              No hay ventas registradas por vendedores en el periodo seleccionado.
            </p>
          ) : (
            <div className="admin-ventas-table mt-3">
              <div className="admin-vendedor-summary-head">
                <span>Vendedor</span>
                <span style={{ textAlign: "center" }}>Pedidos</span>
                <span style={{ textAlign: "right" }}>Total Ventas</span>
                <span style={{ textAlign: "right" }}>Comisión Total</span>
                <span style={{ textAlign: "center" }}>% Efectivo</span>
                <span style={{ textAlign: "center" }}>Acción</span>
              </div>

              {data.vendedores_resumen.map((v) => {
                const isCurrentSelected = String(selectedVendedorId) === String(v.vendedor_id);
                const percEfectivo =
                  Number(v.total_ventas) > 0
                    ? ((Number(v.total_comisiones) / Number(v.total_ventas)) * 100).toFixed(1)
                    : "0.0";
                return (
                  <article
                    className={`admin-vendedor-summary-row ${isCurrentSelected ? "bg-light border-primary" : ""}`}
                    key={v.vendedor_id}
                    style={isCurrentSelected ? { backgroundColor: "#eff6ff" } : undefined}
                  >
                    <div>
                      <strong>{v.nombre}</strong>
                    </div>
                    <div style={{ textAlign: "center" }}>
                      <span className="badge bg-light text-dark border">{v.cantidad_pedidos}</span>
                    </div>
                    <div style={{ textAlign: "right" }}>
                      <strong>{money.format(v.total_ventas)}</strong>
                    </div>
                    <div style={{ textAlign: "right" }}>
                      <span className="vendor-sales-badge-comision">
                        +{money.format(v.total_comisiones)}
                      </span>
                    </div>
                    <div style={{ textAlign: "center" }}>
                      <span className="category-percentage">{percEfectivo}%</span>
                    </div>
                    <div style={{ textAlign: "center" }}>
                      <button
                        type="button"
                        className={`btn btn-sm ${isCurrentSelected ? "btn-primary" : "btn-outline-primary"}`}
                        onClick={() => handleVerPedidosVendedor(v.vendedor_id)}
                        title={`Ver pedidos realizados por ${v.nombre}`}
                      >
                        {isCurrentSelected ? "Filtrado" : "Ver pedidos"}
                      </button>
                    </div>
                  </article>
                );
              })}
            </div>
          )}
        </section>

        {/* 4. Panel: Pedidos Realizados */}
        <section className="content-panel" id="pedidos-realizados-section">
          <div className="panel-heading">
            <div>
              <h2>
                Pedidos Realizados
                {selectedVendedorName ? (
                  <span className="ms-2 badge bg-primary text-white fs-6 fw-normal">
                    Vendedor: {selectedVendedorName}
                  </span>
                ) : null}
              </h2>
              <p>Historial detallado de cada pedido y su comisión calculada.</p>
            </div>
            <div className="d-flex align-items-center gap-2">
              {selectedVendedorId && (
                <button
                  type="button"
                  className="btn btn-outline-secondary btn-sm"
                  onClick={() => setSelectedVendedorId("")}
                >
                  Quitar filtro vendedor
                </button>
              )}
              <span className="panel-count">
                {filteredItems.length} {filteredItems.length === 1 ? "pedido" : "pedidos"}
              </span>
            </div>
          </div>

          {loading ? (
            <p className="mt-4 text-secondary">Cargando pedidos realizados...</p>
          ) : filteredItems.length === 0 ? (
            <div className="text-center py-5">
              <p className="history-filter-empty mb-2">
                {search || hasActiveFilters
                  ? "No se encontraron pedidos con los filtros aplicados."
                  : "No hay pedidos registrados por vendedores en este periodo."}
              </p>
              {selectedVendedorId && (
                <button
                  type="button"
                  className="btn btn-outline-primary btn-sm mt-2"
                  onClick={() => setSelectedVendedorId("")}
                >
                  Ver pedidos de todos los vendedores
                </button>
              )}
            </div>
          ) : (
            <div className="admin-ventas-table mt-3">
              <div className="admin-ventas-head">
                <span>Fecha</span>
                <span>Pedido</span>
                <span>Vendedor</span>
                <span>Cliente / Razón Social</span>
                <span style={{ textAlign: "right" }}>Total Venta</span>
                <span style={{ textAlign: "right" }}>Comisión</span>
                <span style={{ textAlign: "center" }}>Acción</span>
              </div>

              {filteredItems.map((venta) => {
                const orderCode = (venta.pedido_id || "").slice(0, 8).toUpperCase();
                return (
                  <article className="admin-ventas-row" key={venta.id}>
                    <div>
                      <strong>{formatDateTime(venta.created_at, { dateStyle: "short" })}</strong>
                      <small>{formatDateTime(venta.created_at, { timeStyle: "short" })}</small>
                    </div>

                    <div>
                      <span className="category-order-badge">#{orderCode}</span>
                    </div>

                    {/* Columna Vendedor: SOLO NOMBRE */}
                    <div>
                      <strong>{venta.vendedor?.nombre || "Sin vendedor"}</strong>
                    </div>

                    <div>
                      <strong>{venta.cliente?.nombre || "Sin razón social"}</strong>
                      <small>{venta.cliente?.rut ? `RUT: ${venta.cliente.rut}` : "Sin RUT"}</small>
                    </div>

                    <div style={{ textAlign: "right" }}>
                      <strong>{money.format(venta.total_venta)}</strong>
                    </div>

                    <div style={{ textAlign: "right" }}>
                      <span className="vendor-sales-badge-comision">
                        +{money.format(venta.comision_total)}
                      </span>
                    </div>

                    <div style={{ textAlign: "center" }}>
                      <button
                        type="button"
                        className="btn btn-outline-primary btn-sm d-inline-flex align-items-center gap-1"
                        onClick={() => setSelectedVenta(venta)}
                        title="Ver detalle del pedido y productos"
                      >
                        <Eye size={15} />
                        <span>Detalle</span>
                      </button>
                    </div>
                  </article>
                );
              })}
            </div>
          )}
        </section>
      </div>

      {/* Modal Desglose de Detalle de Venta y Comisiones */}
      {selectedVenta && (
        <div className="modal-backdrop-custom" role="presentation">
          <section
            className="category-modal product-modal order-detail-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="admin-vendor-detail-title"
          >
            <header>
              <div>
                <p className="eyebrow">VENTA DE VENDEDOR</p>
                <h2 id="admin-vendor-detail-title">
                  Pedido #{(selectedVenta.pedido_id || "").slice(0, 8).toUpperCase()}
                </h2>
              </div>
              <button
                type="button"
                className="icon-button"
                onClick={() => setSelectedVenta(null)}
                aria-label="Cerrar detalle"
              >
                <X size={19} />
              </button>
            </header>

            <div className="modal-body-custom">
              <div className="order-detail-meta mb-3">
                <span>
                  <strong>Vendedor:</strong> {selectedVenta.vendedor?.nombre || "No asignado"}
                </span>
                <span>
                  <strong>Cliente:</strong> {selectedVenta.cliente?.nombre || selectedVenta.cliente?.rut || "Cliente"}
                </span>
                <span>
                  <strong>RUT:</strong> {selectedVenta.cliente?.rut || "Sin RUT"}
                </span>
                <span>
                  <strong>Fecha:</strong> {formatDateTime(selectedVenta.created_at)}
                </span>
              </div>

              {/* Destacado de Comisión */}
              <div className="vendor-commission-highlight mb-3">
                <div>
                  <strong style={{ color: "#166534" }}>Comisión Generada en esta Venta</strong>
                  <small className="d-block" style={{ color: "#15803d" }}>
                    Calculada automáticamente según el % de comisión de cada categoría
                  </small>
                </div>
                <strong style={{ color: "#15803d", fontSize: "1.3rem" }}>
                  +{money.format(selectedVenta.comision_total)}
                </strong>
              </div>

              {/* Tabla de desglose de productos */}
              <div className="vendor-order-detail-lines">
                <div>
                  <span>Producto</span>
                  <span>Categoría</span>
                  <span>Cant.</span>
                  <span style={{ textAlign: "right" }}>Precio</span>
                  <span style={{ textAlign: "right" }}>Subtotal</span>
                  <span style={{ textAlign: "center" }}>% Com.</span>
                  <span style={{ textAlign: "right" }}>Comisión</span>
                </div>
                {(selectedVenta.detalles || []).map((det) => (
                  <div key={det.id || Math.random()}>
                    <strong>{det.nombre_producto}</strong>
                    <span className="text-secondary">{det.nombre_categoria || "General"}</span>
                    <span>{det.cantidad}</span>
                    <span style={{ textAlign: "right" }}>{money.format(det.precio_unitario)}</span>
                    <span style={{ textAlign: "right" }}>
                      <strong>{money.format(det.subtotal)}</strong>
                    </span>
                    <span style={{ textAlign: "center" }}>
                      <span className="category-percentage">{Number(det.comision_porcentaje || 0)}%</span>
                    </span>
                    <span style={{ textAlign: "right", color: "#15803d", fontWeight: "700" }}>
                      +{money.format(det.comision_monto)}
                    </span>
                  </div>
                ))}
              </div>

              <div className="order-detail-total mt-3">
                <strong>Total Venta: {money.format(selectedVenta.total_venta)}</strong>
                <strong style={{ color: "#15803d" }}>
                  Total Comisión: +{money.format(selectedVenta.comision_total)}
                </strong>
              </div>
            </div>

            <footer>
              <button
                type="button"
                className="btn btn-light"
                onClick={() => setSelectedVenta(null)}
              >
                Cerrar
              </button>
            </footer>
          </section>
        </div>
      )}
    </>
  );
}
