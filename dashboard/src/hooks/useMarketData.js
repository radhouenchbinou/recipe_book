import { useQuery } from "@tanstack/react-query";
import api from "../services/api.js";

export function useMarketData(symbol, days = 30) {
  return useQuery({
    queryKey: ["market-data", symbol, days],
    queryFn: () =>
      api.get(`/api/v1/market-data/${symbol}?days=${days}`).then((r) => r.data.data),
    enabled: !!symbol,
    staleTime: 300_000,
  });
}
