import axios from "axios";

const apiBaseUrl =
  import.meta.env.VITE_API_URL ??
  (import.meta.env.DEV ? "http://localhost:8001/api" : "/api");

export const api = axios.create({
  baseURL: apiBaseUrl,
});

export function setAdminToken(token) {
  if (token) {
    api.defaults.headers.common.Authorization = `Bearer ${token}`;
    return;
  }
  delete api.defaults.headers.common.Authorization;
}

export const setCustomerToken = setAdminToken;
