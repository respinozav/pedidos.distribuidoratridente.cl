import axios from "axios";
import Swal from "sweetalert2";

const apiBaseUrl =
  import.meta.env.VITE_API_URL ??
  (import.meta.env.DEV ? "http://localhost:8001/api" : "/api");

export const api = axios.create({
  baseURL: apiBaseUrl,
});

const STORAGE_KEY_TOKEN = "tridente_auth_token";
const STORAGE_KEY_ROLE = "tridente_auth_role";
const STORAGE_KEY_CUSTOMER = "tridente_customer_profile";

let currentToken = null;
let onAuthExpiredCallback = null;

export function clearSessionStorage() {
  try {
    localStorage.removeItem(STORAGE_KEY_TOKEN);
    localStorage.removeItem(STORAGE_KEY_ROLE);
    localStorage.removeItem(STORAGE_KEY_CUSTOMER);
  } catch {
    // Ignorar excepciones de localStorage
  }
}

export function saveSessionStorage(token, role, customer = null) {
  try {
    if (token) {
      localStorage.setItem(STORAGE_KEY_TOKEN, token);
      if (role) localStorage.setItem(STORAGE_KEY_ROLE, role);
      if (customer) localStorage.setItem(STORAGE_KEY_CUSTOMER, JSON.stringify(customer));
    }
  } catch {
    // Ignorar excepciones de localStorage
  }
}

export function getStoredSession() {
  try {
    const token = localStorage.getItem(STORAGE_KEY_TOKEN);
    const role = localStorage.getItem(STORAGE_KEY_ROLE);
    const customerStr = localStorage.getItem(STORAGE_KEY_CUSTOMER);
    const customer = customerStr ? JSON.parse(customerStr) : null;

    if (!token) return null;

    // Validar si el token expiró
    const base64Url = token.split(".")[1];
    if (!base64Url) return null;
    const base64 = base64Url.replace(/-/g, "+").replace(/_/g, "/");
    const payload = JSON.parse(window.atob(base64));

    if (payload.exp && payload.exp * 1000 <= Date.now()) {
      clearSessionStorage();
      return null;
    }

    return { token, role, customer, payload };
  } catch {
    clearSessionStorage();
    return null;
  }
}

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
  clearSessionStorage();
  delete api.defaults.headers.common["Authorization"];
  delete api.defaults.headers["Authorization"];
}

export const setCustomerToken = setAdminToken;

// Inicializar token guardado al cargar la aplicación si sigue vigente
const initialSession = getStoredSession();
if (initialSession?.token) {
  setAdminToken(initialSession.token);
}

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
      clearSessionStorage();
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
