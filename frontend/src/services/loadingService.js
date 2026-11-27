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
  show(text = "Cargando....", options = {}) {
    loadingCount++;
    loadingText = text || "Cargando....";

    // Si ya está visible en pantalla, actualizar texto si cambió y notificar
    if (isCurrentlyVisible) {
      notify();
      return;
    }

    // Si se requiere feedback visual inmediato (ej. login explícito)
    if (options.immediate) {
      if (showTimer) {
        clearTimeout(showTimer);
        showTimer = null;
      }
      isCurrentlyVisible = true;
      shownAt = Date.now();
      notify();
      return;
    }

    // Iniciar temporizador para mostrar solo si la operación demora ("cuando se pegue el app")
    if (!showTimer) {
      showTimer = setTimeout(() => {
        showTimer = null;
        if (loadingCount > 0) {
          isCurrentlyVisible = true;
          shownAt = Date.now();
          notify();
        }
      }, SHOW_DELAY_MS);
    }
  },

  hide(force = false) {
    if (force) {
      loadingCount = 0;
      if (showTimer) {
        clearTimeout(showTimer);
        showTimer = null;
      }
      if (minDisplayTimer) {
        clearTimeout(minDisplayTimer);
        minDisplayTimer = null;
      }
      isCurrentlyVisible = false;
      notify();
      return;
    }

    loadingCount = Math.max(0, loadingCount - 1);

    if (loadingCount === 0) {
      // Si terminó rápido antes de mostrarse (< 800ms), cancelar el timer para que nunca aparezca
      if (showTimer) {
        clearTimeout(showTimer);
        showTimer = null;
      }

      // Si alcanzó a mostrarse, garantizar una transición suave respetando MIN_DISPLAY_MS
      if (isCurrentlyVisible) {
        const elapsed = Date.now() - shownAt;
        if (elapsed < MIN_DISPLAY_MS) {
          if (minDisplayTimer) clearTimeout(minDisplayTimer);
          minDisplayTimer = setTimeout(() => {
            minDisplayTimer = null;
            if (loadingCount === 0) {
              isCurrentlyVisible = false;
              notify();
            }
          }, MIN_DISPLAY_MS - elapsed);
        } else {
          isCurrentlyVisible = false;
          notify();
        }
      }
    }
  },

  subscribe(listener) {
    listeners.add(listener);
    listener({
      isLoading: isCurrentlyVisible,
      text: loadingText,
    });
    return () => listeners.delete(listener);
  },

  getState() {
    return {
      isLoading: isCurrentlyVisible,
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
