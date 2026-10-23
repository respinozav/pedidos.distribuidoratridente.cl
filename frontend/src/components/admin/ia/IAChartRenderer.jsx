import React from "react";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  PointElement,
  LineElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
} from "chart.js";
import { Bar, Line, Pie, Doughnut } from "react-chartjs-2";
import { BarChart3, TrendingUp, PieChart as PieIcon } from "lucide-react";

// Registrar componentes de Chart.js
ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  PointElement,
  LineElement,
  ArcElement,
  Title,
  Tooltip,
  Legend
);

const DEFAULT_COLORS = [
  "#0ea5e9", // Sky 500
  "#10b981", // Emerald 500
  "#f59e0b", // Amber 500
  "#8b5cf6", // Violet 500
  "#ec4899", // Pink 500
  "#06b6d4", // Cyan 500
  "#64748b", // Slate 500
];

const sanitizeNumber = (val) => {
  if (typeof val === "number") return isNaN(val) ? 0 : val;
  if (!val) return 0;
  const cleaned = String(val).replace(/[$ \s]/g, "").replace(/\./g, "").replace(/,/g, ".");
  const num = parseFloat(cleaned);
  return isNaN(num) ? 0 : num;
};

export default function IAChartRenderer({ chartData }) {
  if (!chartData || !chartData.data) {
    return null;
  }

  const { chartType = "bar", title, description, data } = chartData;

  // Asegurar colores armónicos y datos numéricos estrictamente limpios (Problema 6 resuelto)
  const formattedData = {
    labels: data.labels || [],
    datasets: (data.datasets || []).map((dataset, idx) => ({
      ...dataset,
      data: (dataset.data || []).map(sanitizeNumber),
      backgroundColor:
        dataset.backgroundColor ||
        (chartType === "pie" || chartType === "doughnut"
          ? DEFAULT_COLORS
          : DEFAULT_COLORS[idx % DEFAULT_COLORS.length]),
      borderColor:
        dataset.borderColor ||
        (chartType === "line" ? DEFAULT_COLORS[idx % DEFAULT_COLORS.length] : undefined),
      borderWidth: dataset.borderWidth || (chartType === "line" ? 2 : 1),
      tension: 0.35,
    })),
  };

  const isCurrency =
    (formattedData.datasets[0]?.data || []).some((v) => v > 1000) ||
    /monto|pesos|\$|venta|comprado/i.test(title || "") ||
    /monto|pesos|\$|venta|comprado/i.test(formattedData.datasets[0]?.label || "");

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: chartType === "pie" || chartType === "doughnut" ? "right" : "top",
        labels: {
          font: { family: "Inter, system-ui, sans-serif", size: 12 },
          color: "#475569",
        },
      },
      tooltip: {
        backgroundColor: "rgba(15, 23, 42, 0.9)",
        titleFont: { family: "Inter, system-ui, sans-serif", size: 13, weight: "bold" },
        bodyFont: { family: "Inter, system-ui, sans-serif", size: 12 },
        padding: 10,
        cornerRadius: 8,
        callbacks: {
          label: (ctx) => {
            const rawVal = ctx.raw || 0;
            const dsLabel = ctx.dataset.label || "Valor";
            if (isCurrency) {
              return ` ${dsLabel}: $${Number(rawVal).toLocaleString("es-CL")}`;
            }
            return ` ${dsLabel}: ${Number(rawVal).toLocaleString("es-CL")}`;
          },
        },
      },
    },
    scales:
      chartType === "pie" || chartType === "doughnut"
        ? undefined
        : {
            x: {
              grid: { display: false },
              ticks: { color: "#64748b", font: { size: 11 }, maxRotation: 45, minRotation: 0 },
            },
            y: {
              grid: { color: "#f1f5f9" },
              ticks: {
                color: "#64748b",
                font: { size: 11 },
                callback: (val) => {
                  if (isCurrency) {
                    if (val >= 1000000) return `$${(val / 1000000).toFixed(1)}M`;
                    if (val >= 1000) return `$${(val / 1000).toFixed(0)}K`;
                    return `$${val}`;
                  }
                  return val;
                },
              },
            },
          },
  };

  const getChartIcon = () => {
    switch (chartType) {
      case "line":
        return <TrendingUp size={18} className="text-primary" />;
      case "pie":
      case "doughnut":
        return <PieIcon size={18} className="text-warning" />;
      default:
        return <BarChart3 size={18} className="text-info" />;
    }
  };

  return (
    <div className="ia-chart-card">
      <div className="ia-chart-header">
        <div className="ia-chart-title-wrap">
          {getChartIcon()}
          <div>
            <h4 className="ia-chart-title">{title || "Visualización de Datos"}</h4>
            {description && <p className="ia-chart-desc">{description}</p>}
          </div>
        </div>
      </div>
      <div className="ia-chart-canvas-wrap">
        {chartType === "bar" && <Bar data={formattedData} options={options} />}
        {chartType === "line" && <Line data={formattedData} options={options} />}
        {chartType === "pie" && <Pie data={formattedData} options={options} />}
        {chartType === "doughnut" && <Doughnut data={formattedData} options={options} />}
      </div>
    </div>
  );
}
