import React from "react";
import { AlertTriangle, Clock, ShoppingCart, Sparkles, CheckCircle2 } from "lucide-react";

export default function IAPredictionRenderer({ predictionData }) {
  if (!predictionData || !predictionData.items || !Array.isArray(predictionData.items)) {
    return null;
  }

  const { title = "Predicción de Reposición y Compras", items } = predictionData;

  const getUrgencyBadge = (dias) => {
    if (dias === undefined || dias === null) return null;
    if (dias <= 3) {
      return (
        <span className="ia-urgency-badge is-critical">
          <AlertTriangle size={12} /> Crítico ({dias}d)
        </span>
      );
    }
    if (dias <= 7) {
      return (
        <span className="ia-urgency-badge is-warning">
          <Clock size={12} /> Medio ({dias}d)
        </span>
      );
    }
    return (
      <span className="ia-urgency-badge is-safe">
        <CheckCircle2 size={12} /> Normal ({dias}d)
      </span>
    );
  };

  return (
    <div className="ia-prediction-card">
      <div className="ia-prediction-header">
        <div className="d-flex align-items-center gap-2">
          <Sparkles size={18} className="text-warning" />
          <h4 className="ia-prediction-title">{title}</h4>
        </div>
        <span className="ia-prediction-count">{items.length} sugerencias</span>
      </div>

      <div className="ia-prediction-table-wrap">
        <table className="ia-prediction-table">
          <thead>
            <tr>
              <th>Código / Producto</th>
              <th className="text-center">Stock Actual</th>
              <th className="text-center">Ventas Hist.</th>
              <th className="text-center">Cobertura</th>
              <th className="text-end">Sugerencia Compra</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item, idx) => (
              <tr key={idx}>
                <td>
                  <div className="fw-bold text-dark">{item.nombre || item.producto}</div>
                  {item.codigo && <small className="text-muted">{item.codigo}</small>}
                </td>
                <td className="text-center">
                  <span className={`badge ${Number(item.stock_actual) <= 5 ? "bg-danger" : "bg-secondary"}`}>
                    {item.stock_actual ?? 0} un.
                  </span>
                </td>
                <td className="text-center text-muted">
                  {item.ventas_periodo !== undefined ? `${item.ventas_periodo} un.` : "-"}
                </td>
                <td className="text-center">
                  {getUrgencyBadge(item.dias_cobertura_estimados ?? item.dias_restantes_estimados)}
                </td>
                <td className="text-end">
                  <div className="d-flex align-items-center justify-content-end gap-1 text-success fw-bold">
                    <ShoppingCart size={14} />
                    <span>+{item.sugerencia_compra ?? item.sugerencia ?? 0} un.</span>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
