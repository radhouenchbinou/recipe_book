import React from "react";
import { useNotifications } from "../hooks/useNotifications.js";

const TYPE_COLORS = {
  info:    "var(--accent)",
  success: "#48bb78",
  warn:    "#ed8936",
  error:   "#fc8181",
};

export default function ToastContainer() {
  const { toasts, dismiss } = useNotifications();

  if (!toasts.length) return null;

  return (
    <div style={styles.container}>
      {toasts.map(({ id, msg, type }) => (
        <div key={id} style={{ ...styles.toast, borderLeft: `4px solid ${TYPE_COLORS[type] ?? TYPE_COLORS.info}` }}>
          <span style={styles.msg}>{msg}</span>
          <button style={styles.close} onClick={() => dismiss(id)}>×</button>
        </div>
      ))}
    </div>
  );
}

const styles = {
  container: {
    position: "fixed", bottom: 24, right: 24, zIndex: 9999,
    display: "flex", flexDirection: "column", gap: 8, maxWidth: 360,
  },
  toast: {
    background: "var(--surface)", padding: "12px 16px",
    borderRadius: 8, boxShadow: "0 4px 12px rgba(0,0,0,.3)",
    display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12,
  },
  msg:   { fontSize: 14, color: "var(--text)", flex: 1 },
  close: { background: "none", border: "none", color: "var(--muted)", cursor: "pointer", fontSize: 18, lineHeight: 1 },
};
