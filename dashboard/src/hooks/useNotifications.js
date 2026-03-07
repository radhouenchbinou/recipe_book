import { create } from "zustand";

const useToastStore = create((set, get) => ({
  toasts: [],
  push: (msg, type = "info") => {
    const id = Date.now();
    set({ toasts: [...get().toasts, { id, msg, type }] });
    setTimeout(() => set({ toasts: get().toasts.filter((t) => t.id !== id) }), 5000);
  },
  dismiss: (id) => set({ toasts: get().toasts.filter((t) => t.id !== id) }),
}));

export function useNotifications() {
  const { toasts, push, dismiss } = useToastStore();
  return { toasts, notify: push, dismiss };
}
