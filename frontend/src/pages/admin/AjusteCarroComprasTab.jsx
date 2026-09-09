import React, { useState, useEffect } from "react";
import Swal from "sweetalert2";
import {
  ShoppingCart,
  Clock,
  Trash2,
  RefreshCw,
  Save,
  AlertCircle,
  Package,
  User,
  Phone,
  Mail,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { getActiveCarts, adminDeleteCart } from "../../services/settingsService";
import { formatDateTime, money } from "../../utils/formatters";

export default function AjusteCarroComprasTab({ settings, onSettingsChange, onSaveSettings, saving }) {
  const [carts, setCarts] = useState([]);
  const [loadingCarts, setLoadingCarts] = useState(true);
  const [expandedCartId, setExpandedCartId] = useState(null);
  const [deletingCartId, setDeletingCartId] = useState(null);

  useEffect(() => {
    loadCarts();
    // Actualizar cuenta regresiva cada 30 segundos
    const interval = setInterval(loadCarts, 30000);
    return () => clearInterval(interval);
  }, []);

  const loadCarts = async () => {
    try {
      const data = await getActiveCarts();
      setCarts(data);
    } catch {
      // Ignorar error transitorio si ya se está mostrando
    } finally {
      setLoadingCarts(false);
    }
  };

  const formatRemainingTime = (seconds) => {
    if (seconds <= 0) {
      return { text: "Expirado (pendiente de limpieza)", isExpired: true, isCritical: true };
    }
    const totalMinutes = Math.floor(seconds / 60);
    const hours = Math.floor(totalMinutes / 60);
    const minutes = totalMinutes % 60;

    let text = "";
    if (hours > 0) {
      text = `${hours}h ${minutes}m`;
    } else {
      text = `${minutes} min`;
    }
    return {
      text,
      isExpired: false,
      isCritical: hours < 2, // Crítico si le quedan menos de 2 horas
    };
  };

  const handleDeleteCart = async (cart) => {
    const result = await Swal.fire({
      title: "¿Eliminar carro de compras?",
      html: `
        <p class="mb-2">¿Estás seguro de eliminar el carro de compras de <b>${cart.cliente_nombre}</b>?</p>
        <p class="text-danger small mb-0">
          Esta acción devolverá inmediatamente <b>${cart.total_unidades} unidades</b> tomadas al stock de productos.
        </p>
      `,
      icon: "warning",
      showCancelButton: true,
      confirmButtonColor: "#dc3545",
      cancelButtonColor: "#6c757d",
      confirmButtonText: "Sí, eliminar y devolver stock",
      cancelButtonText: "Cancelar",
    });

    if (!result.isConfirmed) return;

    setDeletingCartId(cart.id);
    try {
      const resp = await adminDeleteCart(cart.id);
      Swal.fire({
        icon: "success",
        title: "Carro eliminado",
        text: resp.message || "Se ha devuelto el stock correctamente.",
        timer: 2500,
        showConfirmButton: false,
      });
      await loadCarts();
    } catch (err) {
      const detail = err.response?.data?.detail || "No fue posible eliminar el carro de compras.";
      Swal.fire("Error", detail, "error");
    } finally {
      setDeletingCartId(null);
    }
  };

  const toggleExpand = (cartId) => {
    setExpandedCartId(expandedCartId === cartId ? null : cartId);
  };

  return (
    <div className="d-flex flex-column gap-4">
      {/* Tarjeta de Configuración de Horas de Expiración */}
      <form onSubmit={onSaveSettings}>
        <div className="settings-card">
          <div className="settings-card-header">
            <div>
              <h3>Parámetros de Expiración del Carro de Compras</h3>
              <p>
                Define el tiempo de vigencia de los carritos. Al cumplirse este lapso sin finalizar la compra,
                el sistema eliminará automáticamente el carrito y reintegrará los productos tomados al inventario.
              </p>
            </div>
            <Clock size={20} className="text-primary" />
          </div>
          <div className="settings-card-body">
            <div className="row g-3 align-items-center">
              <div className="col-12 col-md-6">
                <label htmlFor="carro_compras_expira_horas" className="form-label fw-bold">
                  Tiempo de expiración del carrito (en horas)
                </label>
                <div className="input-group" style={{ maxWidth: "320px" }}>
                  <input
                    id="carro_compras_expira_horas"
                    type="number"
                    min="1"
                    max="720"
                    step="1"
                    className="form-control"
                    name="carro_compras_expira_horas"
                    value={settings.carro_compras_expira_horas || 24}
                    onChange={onSettingsChange}
                    required
                  />
                  <span className="input-group-text">horas</span>
                </div>
                <small className="form-text text-muted mt-2 d-block">
                  Ejemplo: <strong>24 horas</strong>. Cada 60 segundos el job programado verifica carritos inactivos y devuelve los productos reservados.
                </small>
              </div>

              <div className="col-12 col-md-6 d-flex justify-content-md-end align-self-end">
                <button type="submit" className="btn btn-primary d-inline-flex align-items-center gap-2" disabled={saving}>
                  {saving ? (
                    <>
                      <span className="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
                      <span>Guardando...</span>
                    </>
                  ) : (
                    <>
                      <Save size={16} />
                      <span>Guardar Horas de Expiración</span>
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      </form>

      {/* Tarjeta de Carritos de Compra Vigentes */}
      <div className="settings-card">
        <div className="settings-card-header d-flex align-items-center justify-content-between">
          <div>
            <h3>Carritos de Compra Vigentes</h3>
            <p>
              Clientes que tienen productos reservados en su carro de compras actualmente.
            </p>
          </div>
          <div className="d-flex align-items-center gap-2">
            <span className="badge bg-primary px-3 py-2 fs-6">
              {carts.length} {carts.length === 1 ? "Carro Activo" : "Carros Activos"}
            </span>
            <button
              type="button"
              className="btn btn-outline-secondary btn-sm d-inline-flex align-items-center gap-1"
              onClick={loadCarts}
              disabled={loadingCarts}
              title="Refrescar lista"
            >
              <RefreshCw size={14} className={loadingCarts ? "spin" : ""} />
              <span className="d-none d-sm-inline">Actualizar</span>
            </button>
          </div>
        </div>

        <div className="settings-card-body p-0">
          {loadingCarts && carts.length === 0 ? (
            <div className="p-4 text-center text-muted">
              <div className="spinner-border spinner-border-sm text-primary me-2" role="status"></div>
              <span>Cargando carritos vigentes...</span>
            </div>
          ) : carts.length === 0 ? (
            <div className="p-5 text-center">
              <ShoppingCart size={40} className="text-muted mb-2 mx-auto" />
              <h5 className="fw-semibold text-secondary">No hay carritos de compras activos</h5>
              <p className="text-muted small mb-0">
                Cuando los clientes agreguen productos a su pedido, aparecerán aquí con su reserva de stock.
              </p>
            </div>
          ) : (
            <div className="admin-cart-table">
              <div className="admin-cart-head">
                <span>Cliente</span>
                <span>Última Actualización</span>
                <span>Tiempo Restante</span>
                <span>Productos / Total</span>
                <span>Acciones</span>
              </div>
              {carts.map((cart) => {
                const remaining = formatRemainingTime(cart.expira_en_segundos);
                const isExpanded = expandedCartId === cart.id;

                return (
                  <React.Fragment key={cart.id}>
                    <article className={`admin-cart-row ${isExpanded ? "order-row-expanded" : ""}`}>
                      <div>
                        <strong>{cart.cliente_nombre}</strong>
                        <small className="font-monospace">
                          {cart.cliente_rut || "Sin RUT"}
                          {cart.cliente_celular && ` · ${cart.cliente_celular}`}
                        </small>
                      </div>

                      <div>
                        <span>{formatDateTime(cart.updated_at)}</span>
                      </div>

                      <div>
                        {remaining.isExpired ? (
                          <span className="badge-due badge-due-red">
                            {remaining.text}
                          </span>
                        ) : (
                          <span
                            className={`badge-due ${
                              remaining.isCritical ? "badge-due-yellow" : "badge-due-green"
                            }`}
                          >
                            Quedan {remaining.text}
                          </span>
                        )}
                      </div>

                      <div>
                        <strong>{money.format(cart.total)}</strong>
                        <small>
                          {cart.total_items} {cart.total_items === 1 ? "ítem" : "ítems"} ({cart.total_unidades} un.)
                        </small>
                      </div>

                      <div className="admin-cart-actions">
                        <button
                          type="button"
                          className="btn btn-light btn-sm d-inline-flex align-items-center gap-1"
                          onClick={() => toggleExpand(cart.id)}
                          title={isExpanded ? "Ocultar detalle" : "Ver detalle de productos"}
                        >
                          {isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                          <span className="small">{isExpanded ? "Ocultar" : "Detalle"}</span>
                        </button>

                        <button
                          type="button"
                          className="btn btn-outline-danger btn-sm d-inline-flex align-items-center gap-1"
                          onClick={() => handleDeleteCart(cart)}
                          disabled={deletingCartId === cart.id}
                          title="Eliminar carro y devolver productos al inventario"
                        >
                          {deletingCartId === cart.id ? (
                            <span className="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
                          ) : (
                            <Trash2 size={14} />
                          )}
                          <span className="small">Eliminar</span>
                        </button>
                      </div>
                    </article>

                    {/* Fila expandible con el detalle de los productos del carrito con estilo coherente */}
                    {isExpanded && (
                      <div className="cart-items-detail-panel">
                        <div className="cart-items-detail-card">
                          <div className="d-flex align-items-center justify-content-between px-3 py-2 border-bottom bg-light">
                            <div className="d-flex align-items-center gap-2">
                              <Package size={15} className="text-secondary" />
                              <strong className="text-dark" style={{ fontSize: "0.82rem" }}>
                                Productos reservados en este carro:
                              </strong>
                            </div>
                            <span className="badge bg-secondary" style={{ fontSize: "0.72rem" }}>
                              {cart.total_items} {cart.total_items === 1 ? "línea" : "líneas"}
                            </span>
                          </div>

                          <div className="cart-items-detail-head">
                            <span>Código</span>
                            <span>Producto</span>
                            <span>Empaque</span>
                            <span>Cant.</span>
                            <span>Unidades</span>
                            <span>Precio Unit.</span>
                            <span className="text-end">Subtotal</span>
                          </div>

                          {cart.items.map((item) => (
                            <div className="cart-items-detail-row" key={item.id}>
                              <span className="font-monospace text-muted">{item.codigo_producto}</span>
                              <strong>{item.nombre_producto}</strong>
                              <div>
                                <span className={`badge ${item.tipo_empaque === "caja" ? "bg-info text-dark" : "bg-light text-secondary border"}`} style={{ fontSize: "0.72rem" }}>
                                  {item.tipo_empaque === "caja" ? `Caja (${item.cantidad_caja || 1} un.)` : "Unidad"}
                                </span>
                              </div>
                              <span>{item.cantidad}</span>
                              <strong>{item.unidades_totales} un.</strong>
                              <span>{money.format(item.precio_unitario)}</span>
                              <strong className="text-end">{money.format(item.subtotal)}</strong>
                            </div>
                          ))}

                          <div className="cart-items-detail-footer">
                            <div>
                              <span className="text-muted me-2">Unidades Totales Reservadas:</span>
                              <strong className="text-dark">{cart.total_unidades} un.</strong>
                            </div>
                            <div>
                              <span className="text-muted me-2">Total Estimado Carro:</span>
                              <strong className="text-primary fs-6">{money.format(cart.total)}</strong>
                            </div>
                          </div>
                        </div>
                      </div>
                    )}
                  </React.Fragment>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
