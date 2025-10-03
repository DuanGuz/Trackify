import axios from "axios";
import Constants from "expo-constants";

// Ajusta tu IP local si cambia, importante incluir "/" final
const fallback = "http://192.168.100.15:8000/";

const baseURL =
  (Constants?.expoConfig?.extra && Constants.expoConfig.extra.apiBase) ||
  fallback;

export const api = axios.create({
  baseURL,
  timeout: 15000,
});

export const setAuthToken = (token) => {
  if (token) api.defaults.headers.common.Authorization = `Bearer ${token}`;
  else delete api.defaults.headers.common.Authorization;
};
