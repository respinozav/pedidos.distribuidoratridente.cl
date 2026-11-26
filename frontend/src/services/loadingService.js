// Servicio de gestión de estado de carga global
// Permite activar/desactivar el loading modal desde cualquier lugar (API, componentes, hooks)

let loadingCount = 0;
let loadingText = "Cargando....";
let minDisplayTimer = null;
let shownAt = 0;
const MIN_DISPLAY_MS = 200; // Rápido y reactivo: evita micro-parpadeos de 10ms pero no retarda cargas reales
const listeners = new Set();

function notify() {
  const state = {
    isLoading: loadingCount > 0,
    text: loadingText,
  };
  listeners.forEach((listener) => {
    try {
      listener(state);
    } catch (e) {
      console.error("Error en listener de loading:", e);
    }
  });
}

export const loadingService = {
  show(text = "Cargando....") {
    if (minDisplayTimer) {
      clearTimeout(minDisplayTimer);
      minDisplayTimer = null;
    }
    if (loadingCount === 0) {
      shownAt = Date.now();
    }
    loadingCount++;
    loadingText = text || "Cargando....";
    notify();
  },

  hide(force = false) {
    if (force) {
      loadingCount = 0;
      if (minDisplayTimer) {
        clearTimeout(minDisplayTimer);
        minDisplayTimer = null;
      }
      notify();
      return;
    }

    loadingCount = Math.max(0, loadingCount - 1);
    if (loadingCount === 0) {
      const elapsed = Date.now() - shownAt;
      if (elapsed < MIN_DISPLAY_MS) {
        minDisplayTimer = setTimeout(() => {
          if (loadingCount === 0) {
            notify();
          }
        }, MIN_DISPLAY_MS - elapsed);
      } else {
        notify();
      }
    }
  },

  subscribe(listener) {
    listeners.add(listener);
    // Notificar estado actual al suscribirse
    listener({
      isLoading: loadingCount > 0,
      text: loadingText,
    });
    return () => listeners.delete(listener);
  },

  getState() {
    return {
      isLoading: loadingCount > 0,
      text: loadingText,
    };
  },
};

import { useState, useEffect } from "react";

export function useLoading() {
  const [state, setState] = useState(() => loadingService.getState());

  useEffect(() => {
    return loadingService.subscribe(setState);
  }, []);

  return {
    isLoading: state.isLoading,
    loadingText: state.text,
    showLoading: loadingService.show,
    hideLoading: loadingService.hide,
  };
}
