import axios from "axios";
import Swal from "sweetalert2";

const apiBaseUrl =
  import.meta.env.VITE_API_URL ??
  (import.meta.env.DEV ? "http://localhost:8002/api" : "/api");

export const api = axios.create({
  baseURL: apiBaseUrl,
});

const STORAGE_KEY_TOKEN = "tridente_auth_token";
const STORAGE_KEY_ROLE = "tridente_auth_role";
const STORAGE_KEY_CUSTOMER = "tridente_customer_profile";
const STORAGE_KEY_ADMIN_PROFILE = "tridente_admin_profile";
const STORAGE_KEY_TIME_OFFSET = "tridente_auth_time_offset";

let currentToken = null;
let onAuthExpiredCallback = null;

function decodeToken(token) {
  if (!token) return null;
  try {
    const base64Url = token.split(".")[1];
    if (!base64Url) return null;
    const base64 = base64Url.replace(/-/g, "+").replace(/_/g, "/");
    return JSON.parse(window.atob(base64));
  } catch {
    return null;
  }
}

export function clearSessionStorage() {
  try {
    localStorage.removeItem(STORAGE_KEY_TOKEN);
    localStorage.removeItem(STORAGE_KEY_ROLE);
    localStorage.removeItem(STORAGE_KEY_CUSTOMER);
    localStorage.removeItem(STORAGE_KEY_ADMIN_PROFILE);
    localStorage.removeItem(STORAGE_KEY_TIME_OFFSET);
  } catch {
    // Ignorar excepciones de localStorage
  }
}

export function getStoredTimeOffset() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY_TIME_OFFSET);
    return raw !== null ? Number(raw) : 0;
  } catch {
    return 0;
  }
}

export function saveSessionStorage(token, role, customer = null, adminProfile = null) {
  try {
    if (token) {
      localStorage.setItem(STORAGE_KEY_TOKEN, token);
      if (role) localStorage.setItem(STORAGE_KEY_ROLE, role);
      if (customer) localStorage.setItem(STORAGE_KEY_CUSTOMER, JSON.stringify(customer));
      if (adminProfile) localStorage.setItem(STORAGE_KEY_ADMIN_PROFILE, JSON.stringify(adminProfile));

      // Guardar desfase horario entre el reloj local del cliente y el servidor
      const payload = decodeToken(token);
      if (payload?.iat) {
        const offsetSec = Math.round((Date.now() / 1000) - payload.iat);
        localStorage.setItem(STORAGE_KEY_TIME_OFFSET, String(offsetSec));
      }
    }
  } catch {
    // Ignorar excepciones de localStorage
  }
}

export function saveAdminProfileStorage(adminProfile) {
  try {
    if (adminProfile) {
      localStorage.setItem(STORAGE_KEY_ADMIN_PROFILE, JSON.stringify(adminProfile));
    } else {
      localStorage.removeItem(STORAGE_KEY_ADMIN_PROFILE);
    }
  } catch {
    // Ignorar excepciones de localStorage
  }
}

export function getStoredAdminProfile() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY_ADMIN_PROFILE);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function getStoredSession() {
  try {
    const token = localStorage.getItem(STORAGE_KEY_TOKEN);
    const role = localStorage.getItem(STORAGE_KEY_ROLE);
    const customerStr = localStorage.getItem(STORAGE_KEY_CUSTOMER);
    const customer = customerStr ? JSON.parse(customerStr) : null;
    const adminProfile = getStoredAdminProfile();

    if (!token) return null;

    // Validar si el token expiró considerando el desfase del reloj
    const payload = decodeToken(token);
    if (!payload) return null;

    let offsetSec = getStoredTimeOffset();
    if (!offsetSec && payload.iat) {
      offsetSec = Math.round((Date.now() / 1000) - payload.iat);
    }
    const estimatedServerSec = (Date.now() / 1000) - offsetSec;

    if (payload.exp && payload.exp <= estimatedServerSec) {
      clearSessionStorage();
      return null;
    }

    return { token, role, customer, adminProfile, payload };
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
  delete api.defaults.headers.common["Authorization"];
  delete api.defaults.headers["Authorization"];
}

export function setCustomerToken(token) {
  setAdminToken(token);
}

// Interceptor para asegurar que el token actual viaje en todas las peticiones
api.interceptors.request.use((config) => {
  if (currentToken && !config.headers["Authorization"]) {
    config.headers["Authorization"] = `Bearer ${currentToken}`;
  }
  return config;
});

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
