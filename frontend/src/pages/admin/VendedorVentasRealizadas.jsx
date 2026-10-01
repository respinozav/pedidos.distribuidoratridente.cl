import React, { useEffect, useMemo, useState } from "react";
import {
  Eye,
  Plus,
  RotateCcw,
  ShoppingBag,
  X,
} from "lucide-react";
import { api } from "../../services/api";

const money = new Intl.NumberFormat("es-CL", { style: "currency", currency: "CLP" });

function formatDateTime(dateValue, options = {}) {
  if (!dateValue) return "-";
  try {
    const d = typeof dateValue === "string" ? new Date(dateValue) : dateValue;
    return new Intl.DateTimeFormat("es-CL", {
      dateStyle: "short",
      timeStyle: "short",
      timeZone: "America/Santiago",
      ...options,
    }).format(d);
  } catch {
    return String(dateValue);
  }
}

export default function VendedorVentasRealizadas({ onOpenGenerarVenta, isVendedor = true }) {
  const [data, setData] = useState({ total_ventas: 0, total_comisiones: 0, cantidad_pedidos: 0, items: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [desde, setDesde] = useState("");
  const [hasta, setHasta] = useState("");
  const [search, setSearch] = useState("");
  const [selectedVenta, setSelectedVenta] = useState(null);

  async function loadVentas() {
    if (!isVendedor) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError("");
    try {
      const params = {};
      if (desde) params.desde = desde;
      if (hasta) params.hasta = hasta;
      const res = await api.get("/admin/vendedor/ventas", { params });
      setData(res.data);
    } catch {
      setError("No fue posible cargar las ventas realizadas. Intenta nuevamente.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (isVendedor) {
      loadVentas();
    } else {
      setLoading(false);
    }
  }, [desde, hasta, isVendedor]);

  const filteredItems = useMemo(() => {
    if (!search.trim()) return data.items;
    const q = search.trim().toLowerCase();
    return data.items.filter((item) => {
      const clienteNombre = (item.cliente?.nombre || "").toLowerCase();
      const clienteRut = (item.cliente?.rut || "").toLowerCase();
      const pedidoId = (item.pedido_id || "").toLowerCase();
      return clienteNombre.includes(q) || clienteRut.includes(q) || pedidoId.includes(q);
    });
  }, [data.items, search]);

  const filteredTotalVentas = useMemo(() => {
    return filteredItems.reduce((acc, curr) => acc + Number(curr.total_venta || 0), 0);
  }, [filteredItems]);

  const filteredTotalComisiones = useMemo(() => {
    return filteredItems.reduce((acc, curr) => acc + Number(curr.comision_total || 0), 0);
  }, [filteredItems]);

  if (!isVendedor) {
    return (
      <div className="alert alert-warning m-4">
        Esta sección es exclusiva para usuarios con rol Vendedor.
      </div>
    );
  }

  return (
    <>
      <header className="admin-topbar">
        <div className="topbar-title">
          <p className="eyebrow mb-1">MIS VENTAS</p>
          <h1>Ventas Realizadas</h1>
        </div>
        <div className="topbar-actions">
          <span className="topbar-date d-none d-sm-inline">Registro de ventas y comisiones</span>
          <button
            type="button"
            className="btn btn-outline-secondary"
            onClick={loadVentas}
            title="Recargar datos"
          >
            <RotateCcw size={16} />
            <span className="d-none d-sm-inline ms-1">Actualizar</span>
          </button>
          <button
            type="button"
            className="btn btn-primary"
            onClick={onOpenGenerarVenta}
          >
            <Plus size={18} />
            <span>Generar Venta</span>
          </button>
        </div>
      </header>

      <div className="admin-content">
        {/* Banner de resumen nativo */}
        <section className="admin-summary">
          <div>
            <p className="eyebrow">RESUMEN DE COMISIONES</p>
            <h2>Controla tus ventas y ganancias</h2>
            <p>Historial de pedidos generados para clientes y cálculo de comisión según la categoría de cada producto.</p>
          </div>
          <div className="summary-metric">
            <span>{filteredItems.length}</span>
            <small>Ventas registradas</small>
          </div>
        </section>

        {/* Tarjetas métricas nativas del sistema (dashboard-metrics) */}
        <section className="dashboard-metrics">
          <article>
            <span>VENTAS TOTALES</span>
            <strong>{money.format(filteredTotalVentas)}</strong>
            <small>{filteredItems.length} {filteredItems.length === 1 ? "pedido registrado" : "pedidos registrados"}</small>
          </article>
          <article>
            <span>COMISIONES GANADAS</span>
            <strong>{money.format(filteredTotalComisiones)}</strong>
            <small>Calculado por % de categoría</small>
          </article>
          <article>
            <span>TOTAL PEDIDOS</span>
            <strong>{filteredItems.length}</strong>
            <small>En el periodo seleccionado</small>
          </article>
        </section>

        {/* Panel de contenido y filtros nativos */}
        <section className="content-panel">
          <div className="panel-heading">
            <div>
              <h2>Listado de ventas</h2>
              <p>Filtra por cliente, código de pedido o rango de fechas.</p>
            </div>
            <span className="panel-count">
              {filteredItems.length} {filteredItems.length === 1 ? "registro" : "registros"}
            </span>
          </div>

          <div className="admin-order-filters vendor-sales-filters">
            <label className="filter-cliente">
              Buscar
              <input
                className="form-control"
                type="search"
                placeholder="Nombre, RUT o código de pedido..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </label>
            <label className="filter-desde">
              Desde
              <input
                className="form-control"
                type="date"
                value={desde}
                onChange={(e) => setDesde(e.target.value)}
              />
            </label>
            <label className="filter-hasta">
              Hasta
              <input
                className="form-control"
                type="date"
                value={hasta}
                onChange={(e) => setHasta(e.target.value)}
              />
            </label>
            <div className="d-flex align-items-end">
              <button
                type="button"
                className="btn btn-outline-secondary w-100"
                style={{ minHeight: "38px" }}
                onClick={() => {
                  setDesde("");
                  setHasta("");
                  setSearch("");
                }}
                title="Limpiar filtros"
              >
                Limpiar
              </button>
            </div>
          </div>

          {error && <div className="alert alert-danger mt-3 mb-0">{error}</div>}

          {loading ? (
            <p className="mt-4 text-secondary">Cargando ventas realizadas...</p>
          ) : filteredItems.length === 0 ? (
            <p className="history-filter-empty">
              {search || desde || hasta
                ? "No se encontraron ventas con los filtros seleccionados."
                : "Aún no registras ventas. Presiona 'Generar Venta' para comenzar."}
            </p>
          ) : (
            <div className="vendor-sales-table mt-3">
              <div className="vendor-sales-head">
                <span>Fecha</span>
                <span>Pedido</span>
                <span>Cliente / Razón Social</span>
                <span style={{ textAlign: "right" }}>Total Venta</span>
                <span style={{ textAlign: "right" }}>Comisión</span>
                <span>Acción</span>
              </div>
              {filteredItems.map((venta) => {
                const orderCode = (venta.pedido_id || "").slice(0, 8).toUpperCase();
                return (
                  <article className="vendor-sales-row" key={venta.id}>
                    <div>
                      <strong>{formatDateTime(venta.created_at, { dateStyle: "short" })}</strong>
                      <small>{formatDateTime(venta.created_at, { timeStyle: "short" })}</small>
                    </div>

                    <div>
                      <span className="category-order-badge">#{orderCode}</span>
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

                    <div className="vendor-sales-actions">
                      <button
                        type="button"
                        className="btn btn-outline-primary btn-sm d-inline-flex align-items-center gap-1"
                        onClick={() => setSelectedVenta(venta)}
                        title="Ver detalle del pedido y comisiones"
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
            aria-labelledby="vendor-detail-title"
          >
            <header>
              <div>
                <p className="eyebrow">VENTA</p>
                <h2 id="vendor-detail-title">
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
              <div className="order-detail-meta">
                <span><strong>Cliente:</strong> {selectedVenta.cliente?.nombre || selectedVenta.cliente?.rut || "Cliente"}</span>
                <span><strong>RUT:</strong> {selectedVenta.cliente?.rut || "Sin RUT"}</span>
                <span><strong>Fecha:</strong> {formatDateTime(selectedVenta.created_at)}</span>
              </div>

              {/* Destacado de Comisión */}
              <div className="vendor-commission-highlight">
                <div>
                  <strong style={{ color: "#166534" }}>Comisión Ganada en esta Venta</strong>
                  <small className="d-block" style={{ color: "#15803d" }}>
                    Calculada según el porcentaje de comisión de cada categoría
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
                    <span style={{ textAlign: "right" }}><strong>{money.format(det.subtotal)}</strong></span>
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
