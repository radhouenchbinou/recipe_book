import { useEffect, useRef } from "react";
import { io } from "socket.io-client";
import { useAuthStore } from "../stores/authStore.js";

const API_BASE = import.meta.env.VITE_API_URL ?? "http://localhost:3000";

// Singleton socket shared across all useWebSocket calls
let socketInstance = null;

function getSocket(token) {
  if (!socketInstance || socketInstance.disconnected) {
    socketInstance = io(API_BASE, { auth: { token }, autoConnect: true });
  }
  return socketInstance;
}

/**
 * Subscribe to a Socket.io room + event.
 *
 * @param {string} room   - room to join (e.g. "recs", "alerts", "market")
 * @param {string} event  - event name to listen for
 * @param {function} onEvent - callback(payload)
 */
export function useWebSocket(room, event, onEvent) {
  const token = useAuthStore((s) => s.token);
  const callbackRef = useRef(onEvent);
  callbackRef.current = onEvent;

  useEffect(() => {
    if (!token) return;

    const socket = getSocket(token);

    socket.emit("join", room);
    const handler = (payload) => callbackRef.current(payload);
    socket.on(event, handler);

    return () => {
      socket.off(event, handler);
    };
  }, [room, event, token]);
}

/** Disconnect the shared socket (call on logout). */
export function disconnectSocket() {
  if (socketInstance) {
    socketInstance.disconnect();
    socketInstance = null;
  }
}
