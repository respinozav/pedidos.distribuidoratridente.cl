/**
 * Helper para formatear imágenes que pueden venir en Base64 o URL completa
 */
export function formatImageSrc(image) {
  if (!image || typeof image !== "string") return null;
  const trimmed = image.trim();
  if (!trimmed) return null;

  // Ya es una data URI completa
  if (trimmed.startsWith("data:")) {
    return trimmed;
  }

  // Es una URL completa http o https
  if (trimmed.startsWith("http://") || trimmed.startsWith("https://")) {
    return trimmed;
  }

  // Es una ruta relativa estática del frontend (ej. "/logo.png", "/assets/img.jpg")
  if (
    trimmed.startsWith("/") &&
    trimmed.length < 250 &&
    /\.(png|jpg|jpeg|svg|webp|gif|ico)(\?.*)?$/i.test(trimmed)
  ) {
    return trimmed;
  }

  // Si no es URL, es una cadena Base64 (las JPEG en base64 empiezan con /9j/, las PNG con iVBORw0KGgo, etc.)
  let mime = "image/jpeg";
  if (trimmed.startsWith("iVBORw0KGgo")) {
    mime = "image/png";
  } else if (trimmed.startsWith("R0lGOD")) {
    mime = "image/gif";
  } else if (trimmed.startsWith("UklGR")) {
    mime = "image/webp";
  }

  return `data:${mime};base64,${trimmed}`;
}

export const BANNER_COLOR_PRESETS = [
  {
    id: "verde",
    name: "Verde Esmeralda",
    value: "#082620",
    bgStart: "#082620",
    bgEnd: "#041612",
    btnBackground: "linear-gradient(135deg, #23735e 0%, #175242 100%)",
    btnShadow: "0 4px 14px rgba(23, 82, 66, 0.5)",
    tagBg: "rgba(35, 115, 94, 0.28)",
    tagBorder: "rgba(110, 231, 183, 0.45)",
    tagColor: "#6ee7b7",
    badgeBg: "#dcfce7",
    badgeBorder: "#86efac",
    badgeColor: "#15803d",
    subtitleColor: "#d1fae5",
    glowColor: "rgba(35, 115, 94, 0.3)",
  },
  {
    id: "amarillo",
    name: "Amarillo / Dorado",
    value: "#2c2203",
    bgStart: "#2c2203",
    bgEnd: "#181301",
    btnBackground: "linear-gradient(135deg, #946f08 0%, #6e5204 100%)",
    btnShadow: "0 4px 14px rgba(110, 82, 4, 0.5)",
    tagBg: "rgba(234, 179, 8, 0.22)",
    tagBorder: "rgba(250, 204, 21, 0.45)",
    tagColor: "#fde047",
    badgeBg: "#fef9c3",
    badgeBorder: "#fde047",
    badgeColor: "#a16207",
    subtitleColor: "#fef08a",
    glowColor: "rgba(234, 179, 8, 0.25)",
  },
  {
    id: "rojo",
    name: "Rojo",
    value: "#2f0a10",
    bgStart: "#2f0a10",
    bgEnd: "#1a0508",
    btnBackground: "linear-gradient(135deg, #991b28 0%, #6f121c 100%)",
    btnShadow: "0 4px 14px rgba(111, 18, 28, 0.5)",
    tagBg: "rgba(239, 68, 68, 0.24)",
    tagBorder: "rgba(248, 113, 113, 0.45)",
    tagColor: "#fca5a5",
    badgeBg: "#fee2e2",
    badgeBorder: "#fca5a5",
    badgeColor: "#b91c1c",
    subtitleColor: "#fecaca",
    glowColor: "rgba(239, 68, 68, 0.28)",
  },
  {
    id: "azul",
    name: "Azul",
    value: "#091e38",
    bgStart: "#091e38",
    bgEnd: "#040f1d",
    btnBackground: "linear-gradient(135deg, #1b528f 0%, #133c69 100%)",
    btnShadow: "0 4px 14px rgba(19, 60, 105, 0.5)",
    tagBg: "rgba(56, 189, 248, 0.22)",
    tagBorder: "rgba(56, 189, 248, 0.45)",
    tagColor: "#7dd3fc",
    badgeBg: "#e0f2fe",
    badgeBorder: "#7dd3fc",
    badgeColor: "#0369a1",
    subtitleColor: "#e0f2fe",
    glowColor: "rgba(56, 189, 248, 0.28)",
  },
  {
    id: "morado",
    name: "Morado",
    value: "#220c35",
    bgStart: "#220c35",
    bgEnd: "#12051d",
    btnBackground: "linear-gradient(135deg, #6b2aa5 0%, #4b1b75 100%)",
    btnShadow: "0 4px 14px rgba(75, 27, 117, 0.5)",
    tagBg: "rgba(192, 132, 252, 0.22)",
    tagBorder: "rgba(192, 132, 252, 0.45)",
    tagColor: "#d8b4fe",
    badgeBg: "#f3e8ff",
    badgeBorder: "#d8b4fe",
    badgeColor: "#7e22ce",
    subtitleColor: "#f3e8ff",
    glowColor: "rgba(192, 132, 252, 0.28)",
  },
  {
    id: "naranjo",
    name: "Naranjo",
    value: "#351604",
    bgStart: "#351604",
    bgEnd: "#1e0b01",
    btnBackground: "linear-gradient(135deg, #a3440e 0%, #762f08 100%)",
    btnShadow: "0 4px 14px rgba(118, 47, 8, 0.5)",
    tagBg: "rgba(251, 146, 60, 0.22)",
    tagBorder: "rgba(251, 146, 60, 0.45)",
    tagColor: "#fdba74",
    badgeBg: "#ffedd5",
    badgeBorder: "#fdba74",
    badgeColor: "#c2410c",
    subtitleColor: "#ffedd5",
    glowColor: "rgba(251, 146, 60, 0.28)",
  },
];

/**
 * Calcula estilos armónicos para fondo con degradado, botón y tag superior acordes al color elegido
 */
export function getBannerTheme(hexColor = "#082620") {
  const normalizedHex = (hexColor || "#082620").toLowerCase().trim();
  const matchedPreset = BANNER_COLOR_PRESETS.find(
    (p) => p.value.toLowerCase() === normalizedHex
  );
  if (matchedPreset) {
    return matchedPreset;
  }

  let hex = normalizedHex.replace("#", "");
  if (hex.length === 3) {
    hex = hex.split("").map((c) => c + c).join("");
  }
  const r = parseInt(hex.substring(0, 2) || "08", 16) || 8;
  const g = parseInt(hex.substring(2, 4) || "26", 16) || 38;
  const b = parseInt(hex.substring(4, 6) || "20", 16) || 32;

  // Fondo con degradado oscurecido
  const bgEndR = Math.max(2, Math.round(r * 0.5));
  const bgEndG = Math.max(2, Math.round(g * 0.5));
  const bgEndB = Math.max(2, Math.round(b * 0.5));

  // Tono brillante para el botón
  const btnR1 = Math.min(255, Math.max(35, Math.round(r * 2.8 + 45)));
  const btnG1 = Math.min(255, Math.max(35, Math.round(g * 2.8 + 45)));
  const btnB1 = Math.min(255, Math.max(35, Math.round(b * 2.8 + 45)));

  const btnR2 = Math.min(255, Math.max(20, Math.round(r * 2.0 + 15)));
  const btnG2 = Math.min(255, Math.max(20, Math.round(g * 2.0 + 15)));
  const btnB2 = Math.min(255, Math.max(20, Math.round(b * 2.0 + 15)));

  return {
    bgStart: hexColor || "#082620",
    bgEnd: `rgb(${bgEndR}, ${bgEndG}, ${bgEndB})`,
    btnBackground: `linear-gradient(135deg, rgb(${btnR1}, ${btnG1}, ${btnB1}) 0%, rgb(${btnR2}, ${btnG2}, ${btnB2}) 100%)`,
    btnShadow: `0 4px 14px rgba(${btnR2}, ${btnG2}, ${btnB2}, 0.5)`,
    tagBg: `rgba(${btnR1}, ${btnG1}, ${btnB1}, 0.25)`,
    tagBorder: `rgba(${btnR1}, ${btnG1}, ${btnB1}, 0.5)`,
    tagColor: `rgb(${Math.min(255, btnR1 + 75)}, ${Math.min(255, btnG1 + 75)}, ${Math.min(255, btnB1 + 75)})`,
    badgeBg: `rgba(${btnR1}, ${btnG1}, ${btnB1}, 0.12)`,
    badgeBorder: `rgba(${btnR1}, ${btnG1}, ${btnB1}, 0.40)`,
    badgeColor: `rgb(${Math.max(15, Math.round(btnR1 * 0.75))}, ${Math.max(15, Math.round(btnG1 * 0.75))}, ${Math.max(15, Math.round(btnB1 * 0.75))})`,
    subtitleColor: `rgb(${Math.min(255, btnR1 + 60)}, ${Math.min(255, btnG1 + 60)}, ${Math.min(255, btnB1 + 60)})`,
    glowColor: `rgba(${btnR1}, ${btnG1}, ${btnB1}, 0.28)`,
  };
}
