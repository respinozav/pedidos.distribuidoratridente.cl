import React, { useEffect, useMemo, useState } from "react";
import {
  Briefcase,
  Check,
  CheckCircle2,
  ChevronRight,
  Filter,
  Package,
  RotateCcw,
  Search,
  SlidersHorizontal,
  Trash2,
  User,
  UserCheck,
  UserMinus,
  UserPlus,
  Users,
  X,
} from "lucide-react";
import Swal from "sweetalert2";
import { api } from "../../services/api";
import StockAlertBell from "../../components/admin/StockAlertBell";

const money = new Intl.NumberFormat("es-CL", { style: "currency", currency: "CLP" });

export default function AdminCarteraManager() {
  const [data, setData] = useState({
    total_clientes: 0,
    clientes_asignados: 0,
    clientes_sin_asignar: 0,
    vendedores_con_cartera: 0,
    vendedores_disponibles: [],
    items: [],
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Filtros
  const [selectedVendedorId, setSelectedVendedorId] = useState("");
  const [selectedEstado, setSelectedEstado] = useState("todos"); // todos | asignados | sin_asignar
  const [search, setSearch] = useState("");

  // Modal Asignación Individual
  const [assignModalOpen, setAssignModalOpen] = useState(false);
  const [selectedClient, setSelectedClient] = useState(null);
  const [targetVendedorId, setTargetVendedorId] = useState("");
  const [saving, setSaving] = useState(false);

  // Selección múltiple para Asignación Masiva
  const [selectedIds, setSelectedIds] = useState([]);
  const [bulkModalOpen, setBulkModalOpen] = useState(false);
  const [bulkTargetVendedorId, setBulkTargetVendedorId] = useState("");
  const [bulkSaving, setBulkSaving] = useState(false);

  async function loadCartera() {
    setLoading(true);
    setError("");
    try {
      const params = {};
      if (selectedVendedorId) params.vendedor_id = selectedVendedorId;
      if (selectedEstado !== "todos") params.estado_asignacion = selectedEstado;
      if (search.trim()) params.search = search.trim();

      const res = await api.get("/admin/cartera", { params });
      setData(res.data);
    } catch (err) {
      setError("No fue posible cargar la información de la cartera de clientes.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadCartera();
  }, [selectedVendedorId, selectedEstado]);

  // Manejo de búsqueda con pequeño debounce
  useEffect(() => {
    const timer = setTimeout(() => {
      loadCartera();
    }, 250);
    return () => clearTimeout(timer);
  }, [search]);

  const hasActiveFilters =
    Boolean(selectedVendedorId) || selectedEstado !== "todos" || Boolean(search.trim());

  function handleResetFilters() {
    setSelectedVendedorId("");
    setSelectedEstado("todos");
    setSearch("");
  }

  // Abrir modal de asignación individual
  function handleOpenAssignModal(client) {
    setSelectedClient(client);
    setTargetVendedorId(client.vendedor_id || "");
    setAssignModalOpen(true);
  }

  // Guardar asignación individual
  async function handleSaveAssignment(e) {
    e.preventDefault();
    if (!selectedClient) return;

    setSaving(true);
    try {
      const res = await api.put("/admin/cartera/asignar", {
        cliente_id: selectedClient.id,
        vendedor_id: targetVendedorId || null,
      });

      setAssignModalOpen(false);
      setSelectedClient(null);
      await loadCartera();

      Swal.fire({
        icon: "success",
        title: "Cartera actualizada",
        text: res.data.mensaje || "Asignación realizada con éxito.",
        timer: 2000,
        showConfirmButton: false,
      });
    } catch (err) {
      const detail = err.response?.data?.detail || "No fue posible guardar la asignación.";
      Swal.fire("Error", detail, "error");
    } finally {
      setSaving(false);
    }
  }

  // Desasignar cliente directamente
  async function handleUnassign(client) {
    const confirm = await Swal.fire({
      title: "¿Desasignar cliente?",
      html: `¿Estás seguro de quitar a <b>${client.nombre || client.rut}</b> de la cartera de su vendedor?<br/><br/><small class="text-muted">Los futuros pedidos que realice este cliente no acumularán comisiones automáticas hasta que se le asigne un nuevo vendedor.</small>`,
      icon: "warning",
      showCancelButton: true,
      confirmButtonText: "Sí, desasignar",
      cancelButtonText: "Cancelar",
      confirmButtonColor: "#dc2626",
      cancelButtonColor: "#64748b",
    });

    if (!confirm.isConfirmed) return;

    try {
      const res = await api.put(`/admin/cartera/desasignar/${client.id}`);
      await loadCartera();
      Swal.fire({
        icon: "success",
        title: "Cliente desasignado",
        text: res.data.mensaje || "Cliente desasignado exitosamente.",
        timer: 1800,
        showConfirmButton: false,
      });
    } catch (err) {
      const detail = err.response?.data?.detail || "No fue posible desasignar el cliente.";
      Swal.fire("Error", detail, "error");
    }
  }

  // Manejo de checkboxes para selección múltiple
  function toggleSelectAll() {
    if (selectedIds.length === data.items.length) {
      setSelectedIds([]);
    } else {
      setSelectedIds(data.items.map((i) => i.id));
    }
  }

  function toggleSelectItem(id) {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((i) => i !== id) : [...prev, id]
    );
  }

  // Guardar asignación masiva
  async function handleSaveBulkAssignment(e) {
    e.preventDefault();
    if (!selectedIds.length) return;

    setBulkSaving(true);
    try {
      const res = await api.put("/admin/cartera/asignar-masivo", {
        cliente_ids: selectedIds,
        vendedor_id: bulkTargetVendedorId || null,
      });

      setBulkModalOpen(false);
      setSelectedIds([]);
      await loadCartera();

      Swal.fire({
        icon: "success",
        title: "Asignación masiva exitosa",
        text: res.data.mensaje || "Clientes actualizados correctamente.",
        confirmButtonColor: "#146cce",
      });
    } catch (err) {
      const detail = err.response?.data?.detail || "No fue posible realizar la asignación masiva.";
      Swal.fire("Error", detail, "error");
    } finally {
      setBulkSaving(false);
    }
  }

  return (
    <>
      <header className="admin-topbar">
        <div className="topbar-title">
          <p className="eyebrow mb-1">FUERZA DE VENTA</p>
          <h1>Asignación de Cartera</h1>
        </div>
        <div className="topbar-actions">
          <button
            type="button"
            className="btn btn-outline-secondary d-inline-flex align-items-center gap-1"
            onClick={loadCartera}
            disabled={loading}
            title="Recargar cartera"
          >
            <RotateCcw size={16} className={loading ? "spin-animation" : ""} />
            <span className="d-none d-sm-inline">Actualizar</span>
          </button>
          {selectedIds.length > 0 && (
            <button
              type="button"
              className="btn btn-primary d-inline-flex align-items-center gap-2"
              onClick={() => {
                setBulkTargetVendedorId("");
                setBulkModalOpen(true);
              }}
            >
              <Users size={16} />
              <span>Asignar {selectedIds.length} clientes</span>
            </button>
          )}
          <StockAlertBell />
        </div>
      </header>

      <div className="admin-content dashboard-content">
        {/* Banner de resumen */}
        <section className="dashboard-hero mb-3">
          <div>
            <p className="eyebrow">GESTION COMERCIAL</p>
            <h2>Cartera de Clientes por Vendedor</h2>
            <p>
              Asigna clientes a cada vendedor para que cuando el cliente realice pedidos desde la web o la app,
              las comisiones se calculen y abonen automáticamente a su respectivo vendedor.
            </p>
          </div>
        </section>

        {/* Tarjetas métricas nativas del sistema */}
        <section className="dashboard-metrics">
          <article>
            <span>TOTAL CLIENTES</span>
            <strong>{data.total_clientes}</strong>
            <small>Clientes activos registrados</small>
          </article>
          <article style={{ "--metric-color": "#15803d", background: "#e9f8ee" }}>
            <span>CLIENTES ASIGNADOS</span>
            <strong style={{ color: "#15803d" }}>{data.clientes_asignados}</strong>
            <small style={{ color: "#166534" }}>Con vendedor en su cartera</small>
          </article>
          <article style={{ "--metric-color": "#b45309", background: "#fef3c7" }}>
            <span>SIN ASIGNAR</span>
            <strong style={{ color: "#b45309" }}>{data.clientes_sin_asignar}</strong>
            <small style={{ color: "#92400e" }}>Disponibles para asignar</small>
          </article>
          <article>
            <span>VENDEDORES CON CARTERA</span>
            <strong>{data.vendedores_con_cartera}</strong>
            <small>De {data.vendedores_disponibles.length} vendedores activos</small>
          </article>
        </section>

        {/* Filtros debajo de las métricas */}
        <div className="admin-order-filters vendor-sales-filters mb-4">
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

          <label className="filter-estado" style={{ minWidth: "180px" }}>
            Estado Asignación
            <select
              className="form-select"
              value={selectedEstado}
              onChange={(e) => setSelectedEstado(e.target.value)}
            >
              <option value="todos">Todos los clientes</option>
              <option value="asignados">Solo asignados</option>
              <option value="sin_asignar">Solo sin asignar</option>
            </select>
          </label>

          <label className="filter-cliente flex-grow-1">
            Buscar cliente
            <div className="input-group">
              <input
                className="form-control"
                type="search"
                placeholder="Nombre, RUT, correo o celular..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
              {search && (
                <button
                  type="button"
                  className="btn btn-outline-secondary"
                  onClick={() => setSearch("")}
                  title="Limpiar búsqueda"
                >
                  <X size={15} />
                </button>
              )}
            </div>
          </label>

          {hasActiveFilters && (
            <div className="d-flex align-items-end">
              <button
                type="button"
                className="btn btn-outline-secondary"
                style={{ minHeight: "38px", whiteSpace: "nowrap" }}
                onClick={handleResetFilters}
                title="Restablecer filtros"
              >
                <RotateCcw size={15} className="me-1" />
                <span>Restablecer</span>
              </button>
            </div>
          )}
        </div>

        {error && <div className="alert alert-danger mb-4">{error}</div>}

        {/* Barra de acción para selección múltiple */}
        {selectedIds.length > 0 && (
          <div className="alert alert-info d-flex align-items-center justify-content-between mb-3 shadow-sm py-2 px-3">
            <div className="d-flex align-items-center gap-2">
              <CheckCircle2 size={18} className="text-primary" />
              <span>
                <strong>{selectedIds.length}</strong> clientes seleccionados
              </span>
            </div>
            <div className="d-flex gap-2">
              <button
                type="button"
                className="btn btn-sm btn-outline-secondary"
                onClick={() => setSelectedIds([])}
              >
                Deseleccionar
              </button>
              <button
                type="button"
                className="btn btn-sm btn-primary d-inline-flex align-items-center gap-1"
                onClick={() => {
                  setBulkTargetVendedorId("");
                  setBulkModalOpen(true);
                }}
              >
                <Users size={14} />
                <span>Asignar a vendedor</span>
              </button>
            </div>
          </div>
        )}

        {/* Tabla principal de Cartera */}
        <section className="content-panel mb-4">
          <div className="panel-heading">
            <div>
              <h2>Listado de Cartera de Clientes</h2>
              <p>Gestiona a qué vendedor pertenece cada cliente para el cálculo de comisiones automáticas.</p>
            </div>
            <span className="panel-count">{data.items.length} clientes listados</span>
          </div>

          <div className="table-responsive">
            <table className="table align-middle">
              <thead>
                <tr>
                  <th style={{ width: "40px", textAlign: "center" }}>
                    <input
                      type="checkbox"
                      className="form-check-input"
                      checked={data.items.length > 0 && selectedIds.length === data.items.length}
                      onChange={toggleSelectAll}
                      title="Seleccionar todos"
                    />
                  </th>
                  <th>Cliente</th>
                  <th>Contacto</th>
                  <th>Vendedor Asignado</th>
                  <th>Estado</th>
                  <th style={{ textAlign: "right" }}>Historial</th>
                  <th style={{ width: "160px", textAlign: "center" }}>Acciones</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr>
                    <td colSpan={7} className="text-center py-5 text-muted">
                      <div className="spinner-border spinner-border-sm me-2" role="status" />
                      Cargando cartera de clientes...
                    </td>
                  </tr>
                ) : data.items.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="text-center py-5 text-muted">
                      <div className="mb-2">
                        <Users size={36} className="text-secondary opacity-50" />
                      </div>
                      <strong>No se encontraron clientes con los filtros seleccionados</strong>
                      <p className="small mb-0 mt-1">Prueba cambiando el vendedor o el término de búsqueda.</p>
                    </td>
                  </tr>
                ) : (
                  data.items.map((client) => {
                    const isSelected = selectedIds.includes(client.id);
                    const isAssigned = Boolean(client.vendedor_id);
                    return (
                      <tr key={client.id} className={isSelected ? "table-active" : ""}>
                        <td style={{ textAlign: "center" }}>
                          <input
                            type="checkbox"
                            className="form-check-input"
                            checked={isSelected}
                            onChange={() => toggleSelectItem(client.id)}
                          />
                        </td>
                        <td>
                          <div className="fw-bold text-dark">{client.nombre || "Sin nombre registrado"}</div>
                          <small className="text-muted d-block font-monospace">RUT: {client.rut || "-"}</small>
                        </td>
                        <td>
                          {client.correo && <div className="small text-truncate" style={{ maxWidth: "200px" }}>{client.correo}</div>}
                          {client.celular && <small className="text-muted">{client.celular}</small>}
                          {!client.correo && !client.celular && <span className="text-muted small">-</span>}
                        </td>
                        <td>
                          {isAssigned ? (
                            <div className="d-flex align-items-center gap-2">
                              <span
                                style={{
                                  display: "inline-flex",
                                  alignItems: "center",
                                  justifyContent: "center",
                                  width: "28px",
                                  height: "28px",
                                  borderRadius: "50%",
                                  background: "#e0f2fe",
                                  color: "#0284c7",
                                  fontWeight: "bold",
                                  fontSize: "0.75rem",
                                  flexShrink: 0,
                                }}
                              >
                                {client.vendedor_nombre?.slice(0, 2).toUpperCase() || "VD"}
                              </span>
                              <div>
                                <span className="fw-semibold text-dark d-block">
                                  {client.vendedor_nombre}
                                </span>
                                {client.vendedor_correo && (
                                  <small className="text-muted">{client.vendedor_correo}</small>
                                )}
                              </div>
                            </div>
                          ) : (
                            <span className="badge bg-secondary-subtle text-secondary px-2 py-1">
                              Sin vendedor asignado
                            </span>
                          )}
                        </td>
                        <td>
                          {isAssigned ? (
                            <span className="badge bg-success-subtle text-success px-2 py-1 d-inline-flex align-items-center gap-1">
                              <Check size={12} strokeWidth={3} />
                              Asignado
                            </span>
                          ) : (
                            <span className="badge bg-warning-subtle text-warning-emphasis px-2 py-1">
                              Pendiente
                            </span>
                          )}
                        </td>
                        <td style={{ textAlign: "right" }}>
                          <div className="fw-semibold text-dark">{client.total_pedidos} pedidos</div>
                          {Number(client.total_comisiones_generadas) > 0 && (
                            <small className="text-success fw-semibold">
                              {money.format(client.total_comisiones_generadas)} comisiones
                            </small>
                          )}
                        </td>
                        <td style={{ textAlign: "center" }}>
                          <div className="d-flex align-items-center justify-content-center gap-1">
                            <button
                              type="button"
                              className="btn btn-sm btn-outline-primary d-inline-flex align-items-center gap-1"
                              onClick={() => handleOpenAssignModal(client)}
                              title={isAssigned ? "Cambiar vendedor" : "Asignar vendedor"}
                            >
                              <UserCheck size={14} />
                              <span>{isAssigned ? "Cambiar" : "Asignar"}</span>
                            </button>
                            {isAssigned && (
                              <button
                                type="button"
                                className="btn btn-sm btn-outline-danger"
                                onClick={() => handleUnassign(client)}
                                title="Desasignar de la cartera"
                              >
                                <UserMinus size={14} />
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </section>
      </div>

      {/* Modal de Asignación Individual */}
      {assignModalOpen && selectedClient && (
        <div className="modal-backdrop-custom" onClick={() => !saving && setAssignModalOpen(false)}>
          <section
            className="category-modal"
            style={{ maxWidth: "500px" }}
            role="dialog"
            aria-modal="true"
            aria-labelledby="assign-cartera-title"
            onClick={(e) => e.stopPropagation()}
          >
            <header className="focus-group-header">
              <div className="focus-group-title-group">
                <span className="eyebrow d-flex align-items-center gap-1">
                  <Briefcase size={14} /> CARTERA DE CLIENTES
                </span>
                <h2 id="assign-cartera-title">Asignar Vendedor a Cliente</h2>
              </div>
              <button
                className="icon-button"
                type="button"
                onClick={() => setAssignModalOpen(false)}
                disabled={saving}
                aria-label="Cerrar ventana"
              >
                <X size={19} />
              </button>
            </header>

            <form onSubmit={handleSaveAssignment}>
              <div className="modal-body-custom">
                {/* Datos del Cliente */}
                <div className="p-3 bg-light rounded-3 mb-3 border">
                  <div className="text-muted small fw-semibold">CLIENTE SELECCIONADO</div>
                  <div className="fw-bold text-dark fs-6 mt-1">
                    {selectedClient.nombre || "Sin nombre registrado"}
                  </div>
                  <div className="d-flex gap-3 small text-muted mt-1">
                    <span>RUT: {selectedClient.rut || "-"}</span>
                    {selectedClient.correo && <span>{selectedClient.correo}</span>}
                  </div>
                  {selectedClient.vendedor_nombre && (
                    <div className="mt-2 pt-2 border-top small">
                      <span className="text-muted">Vendedor actual: </span>
                      <strong className="text-primary">{selectedClient.vendedor_nombre}</strong>
                    </div>
                  )}
                </div>

                <div className="mb-3">
                  <label htmlFor="target-vendedor-select" className="form-label fw-semibold">
                    Seleccionar Vendedor <span className="text-danger">*</span>
                  </label>
                  <select
                    id="target-vendedor-select"
                    className="form-select"
                    value={targetVendedorId}
                    onChange={(e) => setTargetVendedorId(e.target.value)}
                    disabled={saving}
                  >
                    <option value="">-- Sin Vendedor (Desasignar) --</option>
                    {data.vendedores_disponibles.map((vend) => (
                      <option key={vend.id} value={vend.id}>
                        {vend.nombre} ({vend.correo || "Sin correo"})
                      </option>
                    ))}
                  </select>
                  <div className="form-text">
                    Al seleccionar un vendedor, todos los pedidos futuros que realice este cliente generarán
                    automáticamente comisiones para él.
                  </div>
                </div>
              </div>

              <footer className="focus-group-footer">
                <button
                  type="button"
                  className="btn btn-light"
                  onClick={() => setAssignModalOpen(false)}
                  disabled={saving}
                >
                  Cancelar
                </button>
                <button type="submit" className="btn btn-primary" disabled={saving}>
                  {saving ? (
                    <>
                      <span className="spinner-border spinner-border-sm me-1" role="status" />
                      Guardando...
                    </>
                  ) : (
                    "Guardar Asignación"
                  )}
                </button>
              </footer>
            </form>
          </section>
        </div>
      )}

      {/* Modal de Asignación Masiva */}
      {bulkModalOpen && (
        <div className="modal-backdrop-custom" onClick={() => !bulkSaving && setBulkModalOpen(false)}>
          <section
            className="category-modal"
            style={{ maxWidth: "520px" }}
            role="dialog"
            aria-modal="true"
            aria-labelledby="bulk-cartera-title"
            onClick={(e) => e.stopPropagation()}
          >
            <header className="focus-group-header">
              <div className="focus-group-title-group">
                <span className="eyebrow d-flex align-items-center gap-1">
                  <Users size={14} /> ASIGNACIÓN MASIVA
                </span>
                <h2 id="bulk-cartera-title">Asignar Cartera en Lote</h2>
              </div>
              <button
                className="icon-button"
                type="button"
                onClick={() => setBulkModalOpen(false)}
                disabled={bulkSaving}
                aria-label="Cerrar ventana"
              >
                <X size={19} />
              </button>
            </header>

            <form onSubmit={handleSaveBulkAssignment}>
              <div className="modal-body-custom">
                <div className="alert alert-info py-2 px-3 small mb-3">
                  Se actualizarán simultáneamente <strong>{selectedIds.length}</strong> clientes seleccionados.
                </div>

                <div className="mb-3">
                  <label htmlFor="bulk-vendedor-select" className="form-label fw-semibold">
                    Nuevo Vendedor para los clientes seleccionados:
                  </label>
                  <select
                    id="bulk-vendedor-select"
                    className="form-select"
                    value={bulkTargetVendedorId}
                    onChange={(e) => setBulkTargetVendedorId(e.target.value)}
                    disabled={bulkSaving}
                  >
                    <option value="">-- Quitar Vendedor (Desasignar seleccionados) --</option>
                    {data.vendedores_disponibles.map((vend) => (
                      <option key={vend.id} value={vend.id}>
                        {vend.nombre} ({vend.correo || "Sin correo"})
                      </option>
                    ))}
                  </select>
                  <div className="form-text">
                    {bulkTargetVendedorId
                      ? "Los clientes seleccionados pasarán a formar parte de la cartera del vendedor elegido."
                      : "Al no seleccionar un vendedor, todos los clientes marcados quedarán sin vendedor asignado."}
                  </div>
                </div>
              </div>

              <footer className="focus-group-footer">
                <button
                  type="button"
                  className="btn btn-light"
                  onClick={() => setBulkModalOpen(false)}
                  disabled={bulkSaving}
                >
                  Cancelar
                </button>
                <button type="submit" className="btn btn-primary" disabled={bulkSaving}>
                  {bulkSaving ? (
                    <>
                      <span className="spinner-border spinner-border-sm me-1" role="status" />
                      Asignando...
                    </>
                  ) : (
                    `Aplicar a ${selectedIds.length} clientes`
                  )}
                </button>
              </footer>
            </form>
          </section>
        </div>
      )}
    </>
  );
}
