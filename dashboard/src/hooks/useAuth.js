import { useState, useCallback } from "react";
import { useAuthStore } from "../stores/authStore.js";
import { disconnectSocket } from "./useWebSocket.js";
import api from "../services/api.js";

export function useAuth() {
  const { token, user, setAuth, clearAuth } = useAuthStore();
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const login = useCallback(async (username, password) => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.post("/auth/login", { username, password });
      const { token: t, user: u } = res.data.data;
      setAuth(t, u);
      return true;
    } catch (err) {
      setError(err.response?.data?.error ?? "Login failed");
      return false;
    } finally {
      setLoading(false);
    }
  }, [setAuth]);

  const register = useCallback(async (username, email, password) => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.post("/auth/register", { username, email, password });
      const { token: t, user: u } = res.data.data;
      setAuth(t, u);
      return true;
    } catch (err) {
      setError(err.response?.data?.error ?? "Registration failed");
      return false;
    } finally {
      setLoading(false);
    }
  }, [setAuth]);

  const logout = useCallback(async () => {
    try { await api.post("/auth/logout"); } catch { /* best-effort */ }
    disconnectSocket();
    clearAuth();
  }, [clearAuth]);

  const refreshToken = useCallback(async () => {
    try {
      const res = await api.post("/auth/refresh");
      const { token: t } = res.data.data;
      setAuth(t, user);
      return t;
    } catch {
      clearAuth();
      return null;
    }
  }, [user, setAuth, clearAuth]);

  return { token, user, login, register, logout, refreshToken, error, loading, isAuthenticated: !!token };
}
