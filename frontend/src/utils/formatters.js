export const money = new Intl.NumberFormat("es-CL", { style: "currency", currency: "CLP" });

export function formatDateTime(dateValue, options = {}) {
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
    try {
      const d = typeof dateValue === "string" ? new Date(dateValue) : dateValue;
      return new Intl.DateTimeFormat("es-CL", {
        dateStyle: "short",
        timeStyle: "short",
        ...options,
      }).format(d);
    } catch {
      return String(dateValue);
    }
  }
}
