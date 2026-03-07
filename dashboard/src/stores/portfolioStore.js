import { create } from "zustand";

export const usePortfolioStore = create((set) => ({
  account: null,
  positions: [],
  setAccount: (account) => set({ account }),
  setPositions: (positions) => set({ positions }),
}));
