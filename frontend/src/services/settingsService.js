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
