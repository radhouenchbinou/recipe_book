import { create } from "zustand";

export const useMarketStore = create((set, get) => ({
  quotes: new Map(),
  updateQuote: (symbol, quote) =>
    set({ quotes: new Map(get().quotes).set(symbol, quote) }),
  getQuote: (symbol) => get().quotes.get(symbol),
}));
