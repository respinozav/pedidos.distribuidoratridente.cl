import { api } from "./api";

const API_URL = "/settings";

export const getSettings = async () => {
  const response = await api.get(API_URL);
  return response.data;
};

export const updateSettings = async (data) => {
  const response = await api.put(API_URL, data);
  return response.data;
};

export const getWhatsAppStatus = async () => {
  const response = await api.get("/whatsapp/status");
  return response.data;
};

export const getWhatsAppQR = async () => {
  const response = await api.get("/whatsapp/qr");
  return response.data;
};

export const disconnectWhatsApp = async () => {
  const response = await api.post("/whatsapp/logout");
  return response.data;
};

