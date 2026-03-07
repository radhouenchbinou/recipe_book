import { useQuery } from "@tanstack/react-query";
import api from "../services/api.js";

export function usePortfolio() {
  return useQuery({
    queryKey: ["portfolio"],
    queryFn: () => api.get("/api/v1/portfolio").then((r) => r.data.data),
    staleTime: 30_000,
    refetchInterval: 30_000,
  });
}

export function usePositions() {
  return useQuery({
    queryKey: ["positions"],
    queryFn: () => api.get("/api/v1/portfolio/positions").then((r) => r.data.data),
    staleTime: 30_000,
    refetchInterval: 30_000,
  });
}
