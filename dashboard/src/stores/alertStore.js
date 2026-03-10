import { create } from "zustand";

export const useAlertStore = create((set, get) => ({
  alerts: [],
  setAlerts: (alerts) => set({ alerts }),
  addAlert: (alert) => set({ alerts: [alert, ...get().alerts] }),
  removeAlert: (id) => set({ alerts: get().alerts.filter((a) => a.id !== id) }),
  toggleAlert: (id) =>
    set({
      alerts: get().alerts.map((a) =>
        a.id === id ? { ...a, active: !a.active } : a
      ),
    }),
}));
