import axios from "axios";
import Swal from "sweetalert2";

const apiBaseUrl =
  import.meta.env.VITE_API_URL ??
  (import.meta.env.DEV ? "http://localhost:8001/api" : "/api");

export const api = axios.create({
  baseURL: apiBaseUrl,
});

let currentToken = null;
let onAuthExpiredCallback = null;

export function getActiveToken() {
  return currentToken;
}

export function setOnAuthExpired(callback) {
  onAuthExpiredCallback = callback;
}

export function setAdminToken(token) {
  currentToken = token;
  if (token) {
    api.defaults.headers.common["Authorization"] = `Bearer ${token}`;
    if (api.defaults.headers["Authorization"]) {
      api.defaults.headers["Authorization"] = `Bearer ${token}`;
    }
    return;
  }
  delete api.defaults.headers.common["Authorization"];
  delete api.defaults.headers["Authorization"];
}

export const setCustomerToken = setAdminToken;

// Interceptor global para capturar respuestas 401 (token expirado)
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error?.response?.status;
    const url = error?.config?.url || "";

    // No interceptar intentos fallidos en el formulario de login inicial
    const isLoginEndpoint = url.includes("/login") || url.includes("/clientes/login");

    if (status === 401 && !isLoginEndpoint && currentToken) {
      setAdminToken(null);
      if (onAuthExpiredCallback) {
        onAuthExpiredCallback();
      }
      Swal.fire({
        icon: "warning",
        title: "Sesión caducada",
        text: "Tu sesión ha expirado por límite de tiempo. Por favor ingresa nuevamente con tus credenciales.",
        confirmButtonText: "Iniciar sesión",
        confirmButtonColor: "#0d6efd",
        allowOutsideClick: false,
      });
    }
    return Promise.reject(error);
  }
);
