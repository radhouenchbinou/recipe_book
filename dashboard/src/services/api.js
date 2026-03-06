/**
 * Axios API client — attaches JWT and handles 401 redirects.
 */

import axios from "axios";

const api = axios.create({ baseURL: "/" });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem("token");
      window.location.href = "/login";
    }
    return Promise.reject(err);
  }
);

export const login = (username, password) =>
  api.post("/auth/login", { username, password }).then((r) => r.data.data.token);

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

// ── Phase 2 v2 endpoints ───────────────────────────────────────────────────
export const getBacktest       = (symbol)        =>
  api.get(`/api/v2/backtest/${symbol}`).then((r) => r.data.data);
export const getBacktestList   = ()              =>
  api.get("/api/v2/backtest").then((r) => r.data.data);
export const getPerformance    = ()              =>
  api.get("/api/v2/performance").then((r) => r.data.data);
export const getSymbolPerf     = (symbol)        =>
  api.get(`/api/v2/performance/${symbol}`).then((r) => r.data.data);
export const getRebalancePlan  = ()              =>
  api.get("/api/v2/rebalance").then((r) => r.data.data);
export const executeRebalance  = ()              =>
  api.post("/api/v2/rebalance/execute", { confirm: true }).then((r) => r.data.data);
export const getEquity         = (days = 90)     =>
  api.get("/api/v2/equity", { params: { days } }).then((r) => r.data.data);
export const getSymbolEquity   = (symbol, days = 90) =>
  api.get(`/api/v2/equity/${symbol}`, { params: { days } }).then((r) => r.data.data);

export default api;
