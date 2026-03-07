/**
 * Axios API client — attaches JWT from Zustand authStore, auto-refreshes on 401.
 */

import axios from "axios";
import { useAuthStore } from "../stores/authStore.js";

const api = axios.create({
  baseURL: "/",
  withCredentials: true, // send HttpOnly refresh cookie
});

api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token;
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

let refreshPromise = null;

api.interceptors.response.use(
  (res) => res,
  async (err) => {
    const original = err.config;
    if (err.response?.status === 401 && !original._retry) {
      original._retry = true;
      // Attempt silent token refresh (only once at a time)
      if (!refreshPromise) {
        refreshPromise = api
          .post("/auth/refresh")
          .then((r) => {
            const { token: t } = r.data.data;
            useAuthStore.getState().setAuth(t, useAuthStore.getState().user);
            return t;
          })
          .catch(() => {
            useAuthStore.getState().clearAuth();
            window.location.href = "/login";
          })
          .finally(() => { refreshPromise = null; });
      }
      const newToken = await refreshPromise;
      if (newToken) {
        original.headers.Authorization = `Bearer ${newToken}`;
        return api(original);
      }
    }
    return Promise.reject(err);
  }
);

export const getPortfolio  = ()       => api.get("/api/v1/portfolio").then((r) => r.data.data);
export const getPositions  = ()       => api.get("/api/v1/portfolio/positions").then((r) => r.data.data);
export const getRecommendations = (params) =>
  api.get("/api/v1/recommendations", { params }).then((r) => r.data);
export const getMarketData = (symbol, days = 30) =>
  api.get(`/api/v1/market-data/${symbol}`, { params: { days } }).then((r) => r.data.data);
export const getAlerts     = ()       => api.get("/api/v1/alerts").then((r) => r.data.data);
export const createAlert   = (body)   => api.post("/api/v1/alerts", body).then((r) => r.data.data);
export const deleteAlert   = (id)     => api.delete(`/api/v1/alerts/${id}`);
export const toggleAlert   = (id, active) =>
  api.patch(`/api/v1/alerts/${id}`, { active }).then((r) => r.data.data);
export const getSettings   = ()       => api.get("/api/v1/settings").then((r) => r.data.data);
export const updateSettings = (body)  => api.patch("/api/v1/settings", body).then((r) => r.data.data);

export default api;
