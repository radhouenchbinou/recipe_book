import { useState, useCallback } from "react";
import { login as apiLogin } from "../services/api.js";

export function useAuth() {
  const [token, setToken] = useState(() => localStorage.getItem("token"));
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const login = useCallback(async (username, password) => {
    setLoading(true);
    setError(null);
    try {
      const t = await apiLogin(username, password);
      localStorage.setItem("token", t);
      setToken(t);
      return true;
    } catch (err) {
      setError(err.response?.data?.error ?? "Login failed");
      return false;
    } finally {
      setLoading(false);
    }
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem("token");
    setToken(null);
  }, []);

  return { token, login, logout, error, loading, isAuthenticated: !!token };
}
