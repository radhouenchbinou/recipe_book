import { create } from "zustand";

export const useAnalysisStore = create((set, get) => ({
  scores: new Map(),
  setScores: (symbol, scores) =>
    set({ scores: new Map(get().scores).set(symbol, scores) }),
  getScores: (symbol) => get().scores.get(symbol),
}));
