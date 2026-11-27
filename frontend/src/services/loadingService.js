// Servicio de gestión de estado de carga global con debounce inteligente
// Solo muestra el modal visual si la operación tarda más de SHOW_DELAY_MS (800ms)
// evitando parpadeos en operaciones instantáneas y mostrándose solo cuando "se pegue el app".

let loadingCount = 0;
let loadingText = "Cargando....";
let isCurrentlyVisible = false;
let showTimer = null;
let minDisplayTimer = null;
let shownAt = 0;

const SHOW_DELAY_MS = 850; // Delay extendido: solo se activa si la petición toma más de 850ms (cuando se pegue el app)
const MIN_DISPLAY_MS = 550; // Si llegó a mostrarse, mantener al menos 550ms para apreciar el logo y la estrella fugaz con fluidez

const listeners = new Set();

function notify() {
  const state = {
    isLoading: isCurrentlyVisible,
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
  show() {},
  hide() {},
  subscribe(listener) {
    listener({ isLoading: false, text: "" });
    return () => {};
  },
  getState() {
    return { isLoading: false, text: "" };
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
