import React, { useState, useEffect, useRef } from "react";
import { Bell, AlertTriangle, AlertCircle, X, ChevronRight, Package, CheckCircle2 } from "lucide-react";
import { api } from "../../services/api";

// Almacén en memoria compartido entre todas las instancias de la campana
let cachedAlertProducts = [];
let hasFetchedAlerts = false;
let isFetchingAlerts = false;
const alertSubscribers = new Set();

export async function refreshStockAlerts() {
  if (isFetchingAlerts) return;
  isFetchingAlerts = true;
  try {
    const res = await api.get("/admin/productos/alertas-stock");
    if (Array.isArray(res.data)) {
      cachedAlertProducts = res.data;
      hasFetchedAlerts = true;
      alertSubscribers.forEach((fn) => fn(cachedAlertProducts));
    }
  } catch (err) {
    console.error("Error al cargar productos para alerta de stock:", err);
  } finally {
    isFetchingAlerts = false;
  }
}

const imageSource = (value) => {
  if (!value) return null;
  if (value.startsWith("data:") || value.startsWith("http")) return value;
  return `data:image/jpeg;base64,${value}`;
};

export default function StockAlertBell({ initialProducts = null }) {
  const [alertProducts, setAlertProducts] = useState(
    Array.isArray(initialProducts) ? initialProducts : cachedAlertProducts
  );
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const containerRef = useRef(null);

  useEffect(() => {
    const subscriber = (items) => setAlertProducts(items);
    alertSubscribers.add(subscriber);

    if (!hasFetchedAlerts) {
      refreshStockAlerts();
    } else {
      setAlertProducts(cachedAlertProducts);
    }

    // Actualizar periódicamente cada 60 segundos o cuando la ventana recupere foco
    const interval = setInterval(refreshStockAlerts, 60000);
    const onFocus = () => refreshStockAlerts();
    const onStockAlertRefresh = () => refreshStockAlerts();

    window.addEventListener("focus", onFocus);
    window.addEventListener("stock-alert-refresh", onStockAlertRefresh);

    return () => {
      alertSubscribers.delete(subscriber);
      clearInterval(interval);
      window.removeEventListener("focus", onFocus);
      window.removeEventListener("stock-alert-refresh", onStockAlertRefresh);
    };
  }, []);

  // Si cambia initialProducts desde props, sincronizar
  useEffect(() => {
    if (initialProducts && Array.isArray(initialProducts)) {
      setAlertProducts(initialProducts);
    }
  }, [initialProducts]);

  // Manejador para cerrar dropdown al hacer clic fuera
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (containerRef.current && !containerRef.current.contains(event.target)) {
        setDropdownOpen(false);
      }
    };
    if (dropdownOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [dropdownOpen]);

  const alertCount = alertProducts.length;

  return (
    <div className="stock-alert-container" ref={containerRef}>
      <button
        type="button"
        className={`stock-alert-bell-btn ${dropdownOpen ? "is-active" : ""} ${alertCount > 0 ? "has-alerts" : ""}`}
        onClick={() => {
          setDropdownOpen((prev) => !prev);
        }}
        title={alertCount > 0 ? `${alertCount} producto(s) con alerta de stock` : "Alertas de stock"}
        aria-label="Campana de alertas de stock"
        aria-expanded={dropdownOpen}
      >
        <Bell size={19} className="stock-alert-bell-icon" />
        {alertCount > 0 && (
          <span className="stock-alert-badge">
            {alertCount > 99 ? "99+" : alertCount}
          </span>
        )}
      </button>

      {/* Menú chico desplegable */}
      {dropdownOpen && (
        <div className="stock-alert-dropdown" role="menu">
          <div className="stock-alert-dropdown-header">
            <span>Notificaciones</span>
            {alertCount > 0 ? (
              <span className="stock-alert-count-pill">{alertCount} en alerta</span>
            ) : (
              <span className="stock-alert-count-pill success">Sin alertas</span>
            )}
          </div>
          <div className="stock-alert-dropdown-body">
            <button
              type="button"
              className="stock-alert-item"
              onClick={() => {
                setDropdownOpen(false);
                setModalOpen(true);
              }}
            >
              <div className={`stock-alert-item-icon ${alertCount > 0 ? "has-alert" : ""}`}>
                <AlertTriangle size={18} />
              </div>
              <div className="stock-alert-item-content">
                <strong className="stock-alert-item-title">Alerta de Productos en Stock</strong>
                <small className="stock-alert-item-subtitle">
                  {alertCount > 0
                    ? `${alertCount} producto${alertCount === 1 ? "" : "s"} con stock crítico`
                    : "Inventario al día (sin alertas)"}
                </small>
              </div>
              <ChevronRight size={16} className="stock-alert-item-arrow" />
            </button>
          </div>
        </div>
      )}

      {/* Modal con listado de productos */}
      {modalOpen && (
        <div
          className="modal-backdrop-custom"
          role="presentation"
          onClick={() => setModalOpen(false)}
        >
          <div
            className="category-modal stock-alert-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="stock-alert-title"
            onClick={(e) => e.stopPropagation()}
          >
            <header>
              <div>
                <p className="eyebrow">INVENTARIO</p>
                <h2 id="stock-alert-title">Alerta de Productos en Stock</h2>
              </div>
              <button
                type="button"
                className="icon-button"
                onClick={() => setModalOpen(false)}
                aria-label="Cerrar modal"
              >
                <X size={19} />
              </button>
            </header>

            <div className="modal-body-custom">
              {alertCount === 0 ? (
                <div className="stock-alert-empty-state">
                  <div className="stock-alert-empty-icon">
                    <CheckCircle2 size={38} />
                  </div>
                  <strong>¡Inventario al día!</strong>
                  <p className="text-secondary mb-0">
                    No existen productos que hayan alcanzado o bajado de su umbral de notificación de stock.
                  </p>
                </div>
              ) : (
                <>
                  <div className="stock-alert-banner">
                    <AlertCircle size={18} />
                    <span>
                      Se detectaron <strong>{alertCount}</strong> producto{alertCount === 1 ? "" : "s"} con stock disponible menor o igual a su umbral de aviso.
                    </span>
                  </div>

                  <div className="stock-alert-table-container">
                    <table className="stock-alert-table">
                      <thead>
                        <tr>
                          <th>Código</th>
                          <th>Producto</th>
                          <th className="text-center">Stock disponible</th>
                          <th className="text-center">Umbral aviso</th>
                        </tr>
                      </thead>
                      <tbody>
                        {alertProducts.map((prod) => {
                          const stockNum = Number(prod.cantidad);
                          const isCritical = stockNum <= 0;
                          return (
                            <tr key={prod.id}>
                              <td>
                                <span className="stock-alert-code">{prod.codigo || "-"}</span>
                              </td>
                              <td>
                                <div className="stock-alert-prod-cell">
                                  <span className="stock-alert-prod-thumb">
                                    {prod.imagen_url ? (
                                      <img src={imageSource(prod.imagen_url)} alt={prod.nombre} />
                                    ) : (
                                      <Package size={17} />
                                    )}
                                  </span>
                                  <div className="stock-alert-prod-info">
                                    <strong className="stock-alert-prod-name" title={prod.nombre}>
                                      {prod.nombre}
                                    </strong>
                                  </div>
                                </div>
                              </td>
                              <td className="text-center">
                                <span className={`stock-status-pill ${isCritical ? "critical" : "warning"}`}>
                                  {stockNum} {stockNum === 1 || stockNum === -1 ? "unidad" : "unidades"}
                                </span>
                              </td>
                              <td className="text-center">
                                <span className="stock-threshold-pill">
                                  &le; {prod.stock_notificacion} uds.
                                </span>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </>
              )}
            </div>

            <footer>
              <button
                type="button"
                className="btn btn-primary"
                onClick={() => setModalOpen(false)}
              >
                Entendido / Cerrar
              </button>
            </footer>
          </div>
        </div>
      )}
    </div>
  );
}
