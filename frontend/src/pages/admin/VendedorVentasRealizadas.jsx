import React, { useEffect, useMemo, useState } from "react";
import {
  AlertCircle,
  Calendar,
  CheckCircle2,
  ChevronRight,
  ClipboardList,
  DollarSign,
  Eye,
  FileText,
  Filter,
  Plus,
  RotateCcw,
  Search,
  ShoppingBag,
  TrendingUp,
  User,
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

export default function VendedorVentasRealizadas({ onOpenGenerarVenta, isVendedor }) {
  const [data, setData] = useState({ total_ventas: 0, total_comisiones: 0, cantidad_pedidos: 0, items: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [desde, setDesde] = useState("");
  const [hasta, setHasta] = useState("");
  const [search, setSearch] = useState("");
  const [selectedVenta, setSelectedVenta] = useState(null);

  async function loadVentas() {
    setLoading(true);
    setError("");
    try {
      const params = {};
      if (desde) params.desde = desde;
      if (hasta) params.hasta = hasta;
      const res = await api.get("/admin/vendedor/ventas", { params });
      setData(res.data);
    } catch (err) {
      setError("No fue posible cargar las ventas realizadas. Intenta nuevamente.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadVentas();
  }, [desde, hasta]);

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

  return (
    <div className="vendedor-ventas-view">
      <header className="admin-topbar">
        <div className="topbar-title">
          <p className="eyebrow mb-1">MIS VENTAS</p>
          <h1>Ventas Realizadas</h1>
        </div>
        <div className="topbar-actions">
          <button
            type="button"
            className="btn btn-outline-secondary me-2"
            onClick={loadVentas}
            title="Recargar datos"
          >
            <RotateCcw size={16} className="me-1" />
            Actualizar
          </button>
          <button
            type="button"
            className="btn btn-primary"
            onClick={onOpenGenerarVenta}
          >
            <Plus size={18} className="me-1" />
            Generar Venta
          </button>
        </div>
      </header>

      <div className="admin-content">
        {/* KPI Cards */}
        <section className="row g-3 mb-4">
          <div className="col-12 col-md-4">
            <div className="card shadow-sm border-0 h-100 p-3" style={{ borderRadius: "12px", background: "linear-gradient(135deg, #f8fafc 0%, #edf2f7 100%)" }}>
              <div className="d-flex align-items-center justify-content-between mb-2">
                <span className="text-muted fw-bold small text-uppercase">Total Ventas</span>
                <span className="badge bg-primary-subtle text-primary p-2" style={{ borderRadius: "8px" }}>
                  <ShoppingBag size={20} />
                </span>
              </div>
              <h2 className="fs-3 fw-bold text-dark mb-1">
                {money.format(filteredTotalVentas)}
              </h2>
              <small className="text-muted">
                {filteredItems.length} {filteredItems.length === 1 ? "pedido registrado" : "pedidos registrados"}
              </small>
            </div>
          </div>

          <div className="col-12 col-md-4">
            <div className="card shadow-sm border-0 h-100 p-3" style={{ borderRadius: "12px", background: "linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%)" }}>
              <div className="d-flex align-items-center justify-content-between mb-2">
                <span className="text-success fw-bold small text-uppercase">Comisiones Ganadas</span>
                <span className="badge bg-success-subtle text-success p-2" style={{ borderRadius: "8px" }}>
                  <TrendingUp size={20} />
                </span>
              </div>
              <h2 className="fs-3 fw-bold text-success mb-1">
                {money.format(filteredTotalComisiones)}
              </h2>
              <small className="text-muted">
                Calculado según el % por categoría vendida
              </small>
            </div>
          </div>

          <div className="col-12 col-md-4">
            <div className="card shadow-sm border-0 h-100 p-3" style={{ borderRadius: "12px", background: "linear-gradient(135deg, #f8fafc 0%, #edf2f7 100%)" }}>
              <div className="d-flex align-items-center justify-content-between mb-2">
                <span className="text-muted fw-bold small text-uppercase">Total de Pedidos</span>
                <span className="badge bg-secondary-subtle text-secondary p-2" style={{ borderRadius: "8px" }}>
                  <ClipboardList size={20} />
                </span>
              </div>
              <h2 className="fs-3 fw-bold text-dark mb-1">
                {filteredItems.length}
              </h2>
              <small className="text-muted">
                Ventas asociadas al vendedor
              </small>
            </div>
          </div>
        </section>

        {/* Filters */}
        <section className="content-panel mb-4 p-3" style={{ borderRadius: "12px" }}>
          <div className="row g-2 align-items-end">
            <div className="col-12 col-md-4">
              <label className="form-label small fw-bold text-secondary mb-1">
                Buscar cliente o pedido
              </label>
              <div className="search-field w-100">
                <Search size={17} />
                <input
                  type="search"
                  className="form-control"
                  placeholder="Nombre, RUT o código..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                />
              </div>
            </div>

            <div className="col-6 col-md-3">
              <label className="form-label small fw-bold text-secondary mb-1">
                Desde
              </label>
              <input
                type="date"
                className="form-control"
                value={desde}
                onChange={(e) => setDesde(e.target.value)}
              />
            </div>

            <div className="col-6 col-md-3">
              <label className="form-label small fw-bold text-secondary mb-1">
                Hasta
              </label>
              <input
                type="date"
                className="form-control"
                value={hasta}
                onChange={(e) => setHasta(e.target.value)}
              />
            </div>

            <div className="col-12 col-md-2 d-flex gap-2">
              <button
                type="button"
                className="btn btn-outline-secondary w-100"
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
        </section>

        {/* Error Alert */}
        {error && <div className="alert alert-danger mb-4">{error}</div>}

        {/* Table Panel */}
        <section className="content-panel" style={{ borderRadius: "12px", overflow: "hidden" }}>
          <div className="panel-heading d-flex justify-content-between align-items-center p-3 border-bottom">
            <div>
              <h2 className="fs-5 mb-0 fw-bold">Registro de Ventas y Comisiones</h2>
              <small className="text-muted">Historial de pedidos generados para clientes</small>
            </div>
            <span className="badge bg-light text-dark border px-3 py-2">
              {filteredItems.length} registros
            </span>
          </div>

          {loading ? (
            <div className="text-center p-5 text-secondary">
              <div className="spinner-border spinner-border-sm me-2" role="status" />
              Cargando historial de ventas...
            </div>
          ) : filteredItems.length === 0 ? (
            <div className="text-center p-5 text-secondary">
              <ShoppingBag size={48} className="text-muted mb-3 opacity-50" />
              <p className="fs-6 mb-1 fw-bold text-dark">No hay ventas registradas</p>
              <p className="small text-muted mb-3">
                {search || desde || hasta
                  ? "No se encontraron ventas que coincidan con los filtros aplicados."
                  : "Aún no has generado ventas para clientes. Pincha en 'Generar Venta' para comenzar."}
              </p>
              <button
                type="button"
                className="btn btn-primary btn-sm"
                onClick={onOpenGenerarVenta}
              >
                <Plus size={16} className="me-1" />
                Generar mi primera venta
              </button>
            </div>
          ) : (
            <div className="table-responsive">
              <table className="table table-hover align-middle mb-0">
                <thead className="table-light">
                  <tr className="small text-uppercase text-secondary">
                    <th scope="col" style={{ paddingLeft: "20px" }}>Fecha</th>
                    <th scope="col">Pedido</th>
                    <th scope="col">Cliente / Razón Social</th>
                    {!isVendedor && <th scope="col">Vendedor</th>}
                    <th scope="col" className="text-end">Total Venta</th>
                    <th scope="col" className="text-end">Comisión Ganada</th>
                    <th scope="col" className="text-center" style={{ paddingRight: "20px" }}>Acción</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredItems.map((venta) => {
                    const orderCode = (venta.pedido_id || "").slice(0, 8).toUpperCase();
                    return (
                      <tr key={venta.id}>
                        <td style={{ paddingLeft: "20px", whiteSpace: "nowrap" }}>
                          <span className="fw-semibold text-dark">
                            {formatDateTime(venta.created_at, { dateStyle: "short" })}
                          </span>
                          <small className="text-muted d-block" style={{ fontSize: "0.75rem" }}>
                            {formatDateTime(venta.created_at, { timeStyle: "short" })}
                          </small>
                        </td>

                        <td>
                          <span className="badge bg-secondary-subtle text-secondary font-monospace fw-bold">
                            #{orderCode}
                          </span>
                        </td>

                        <td>
                          <div className="fw-bold text-dark">
                            {venta.cliente?.nombre || "Sin razón social"}
                          </div>
                          <small className="text-muted">
                            {venta.cliente?.rut ? `RUT: ${venta.cliente.rut}` : "Sin RUT"}
                          </small>
                        </td>

                        {!isVendedor && (
                          <td>
                            <span className="badge bg-light text-dark border">
                              {venta.vendedor?.nombre || "Vendedor"}
                            </span>
                          </td>
                        )}

                        <td className="text-end fw-bold text-dark">
                          {money.format(venta.total_venta)}
                        </td>

                        <td className="text-end">
                          <span
                            className="badge bg-success-subtle text-success fs-6 fw-bold px-2 py-1"
                            title="Comisión calculada según categoría"
                          >
                            +{money.format(venta.comision_total)}
                          </span>
                        </td>

                        <td className="text-center" style={{ paddingRight: "20px" }}>
                          <button
                            type="button"
                            className="btn btn-outline-primary btn-sm d-inline-flex align-items-center gap-1"
                            onClick={() => setSelectedVenta(venta)}
                            title="Ver desglose de productos y comisiones"
                          >
                            <Eye size={15} />
                            <span>Ver Detalle</span>
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </div>

      {/* Modal Desglose de Detalle de Venta y Comisiones */}
      {selectedVenta && (
        <div className="modal-backdrop-custom" role="presentation">
          <div
            className="category-modal"
            style={{ maxWidth: "750px", width: "95%" }}
            role="dialog"
            aria-modal="true"
          >
            <header className="d-flex justify-content-between align-items-center border-bottom p-3">
              <div>
                <p className="eyebrow mb-1">DETALLE DE VENTA Y COMISIÓN</p>
                <h2 className="fs-5 mb-0">
                  Pedido #{(selectedVenta.pedido_id || "").slice(0, 8).toUpperCase()}
                </h2>
              </div>
              <button
                type="button"
                className="icon-button"
                onClick={() => setSelectedVenta(null)}
                aria-label="Cerrar detalle"
              >
                <X size={20} />
              </button>
            </header>

            <div className="modal-body-custom p-4">
              <div className="row g-3 mb-4 p-3 bg-light rounded-3">
                <div className="col-12 col-sm-6">
                  <small className="text-muted d-block">Cliente / Razón Social</small>
                  <strong className="text-dark fs-6">
                    {selectedVenta.cliente?.nombre || "Sin razón social"}
                  </strong>
                  <div className="small text-muted">{selectedVenta.cliente?.rut || "Sin RUT"}</div>
                </div>

                <div className="col-6 col-sm-3">
                  <small className="text-muted d-block">Fecha de Venta</small>
                  <strong className="text-dark">
                    {formatDateTime(selectedVenta.created_at)}
                  </strong>
                </div>

                <div className="col-6 col-sm-3 text-sm-end">
                  <small className="text-muted d-block">Total Venta</small>
                  <strong className="fs-6 text-dark">
                    {money.format(selectedVenta.total_venta)}
                  </strong>
                </div>
              </div>

              {/* Commission banner */}
              <div className="alert alert-success d-flex align-items-center justify-content-between p-3 mb-4" style={{ borderRadius: "10px" }}>
                <div className="d-flex align-items-center gap-2">
                  <TrendingUp size={22} className="text-success" />
                  <div>
                    <strong>Total Comisión Ganada en este Pedido:</strong>
                    <div className="small text-success">
                      Calculada por porcentaje según la categoría de cada producto
                    </div>
                  </div>
                </div>
                <div className="fs-4 fw-bold text-success">
                  {money.format(selectedVenta.comision_total)}
                </div>
              </div>

              {/* Product breakdown table */}
              <h3 className="fs-6 fw-bold mb-2">Desglose por Producto Vendido</h3>
              <div className="table-responsive border rounded-3">
                <table className="table table-sm align-middle mb-0">
                  <thead className="table-light">
                    <tr className="small text-secondary">
                      <th scope="col">Producto</th>
                      <th scope="col">Categoría</th>
                      <th scope="col" className="text-center">Cant.</th>
                      <th scope="col" className="text-end">Precio Un.</th>
                      <th scope="col" className="text-end">Subtotal</th>
                      <th scope="col" className="text-center">% Comis.</th>
                      <th scope="col" className="text-end">Comisión</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(selectedVenta.detalles || []).map((det) => (
                      <tr key={det.id || Math.random()}>
                        <td className="fw-semibold text-dark">
                          {det.nombre_producto}
                        </td>
                        <td>
                          <span className="badge bg-light text-secondary border">
                            {det.nombre_categoria || "General"}
                          </span>
                        </td>
                        <td className="text-center fw-bold">{det.cantidad}</td>
                        <td className="text-end">{money.format(det.precio_unitario)}</td>
                        <td className="text-end fw-bold">{money.format(det.subtotal)}</td>
                        <td className="text-center">
                          <span className="badge bg-info-subtle text-info fw-bold">
                            {Number(det.comision_porcentaje || 0)}%
                          </span>
                        </td>
                        <td className="text-end text-success fw-bold">
                          +{money.format(det.comision_monto)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                  <tfoot className="table-light">
                    <tr>
                      <th colSpan={4} className="text-end">Total:</th>
                      <th className="text-end fw-bold">{money.format(selectedVenta.total_venta)}</th>
                      <th className="text-center text-muted small">Total Comisión</th>
                      <th className="text-end text-success fw-bold fs-6">
                        +{money.format(selectedVenta.comision_total)}
                      </th>
                    </tr>
                  </tfoot>
                </table>
              </div>
            </div>

            <footer className="border-top p-3 d-flex justify-content-end">
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => setSelectedVenta(null)}
              >
                Cerrar
              </button>
            </footer>
          </div>
        </div>
      )}
    </div>
  );
}
