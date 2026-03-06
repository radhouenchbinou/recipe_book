import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getAlerts, createAlert, deleteAlert, toggleAlert } from "../services/api.js";

const ALERT_TYPES = ["price_above","price_below","score_above","score_below","recommendation"];
const SYMBOLS = ["SPY","QQQ","GLD","AAPL","MSFT","NVDA"];

export default function AlertsPage() {
  const qc = useQueryClient();
  const [form, setForm] = useState({ symbol: "SPY", alert_type: "price_above", threshold: "", message: "" });
  const [formError, setFormError] = useState(null);

  const { data: alerts, isLoading } = useQuery({ queryKey: ["alerts"], queryFn: getAlerts });

  const createMutation = useMutation({
    mutationFn: createAlert,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["alerts"] }); setForm({ symbol:"SPY", alert_type:"price_above", threshold:"", message:"" }); setFormError(null); },
    onError: (e) => setFormError(e.response?.data?.error ?? "Failed to create alert"),
  });

  const deleteMutation = useMutation({
    mutationFn: deleteAlert,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["alerts"] }),
  });

  const toggleMutation = useMutation({
    mutationFn: ({ id, active }) => toggleAlert(id, active),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["alerts"] }),
  });

  function handleCreate(e) {
    e.preventDefault();
    const body = { symbol: form.symbol, alert_type: form.alert_type };
    if (form.threshold) body.threshold = parseFloat(form.threshold);
    if (form.message) body.message = form.message;
    createMutation.mutate(body);
  }

  return (
    <div>
      <h2 style={styles.title}>Alerts</h2>

      {/* Create form */}
      <div style={styles.card}>
        <h3 style={{ marginBottom: 16, fontSize: 15 }}>New Alert</h3>
        <form onSubmit={handleCreate} style={styles.formGrid}>
          <select style={styles.input} value={form.symbol} onChange={(e) => setForm({ ...form, symbol: e.target.value })}>
            {SYMBOLS.map((s) => <option key={s}>{s}</option>)}
          </select>
          <select style={styles.input} value={form.alert_type} onChange={(e) => setForm({ ...form, alert_type: e.target.value })}>
            {ALERT_TYPES.map((t) => <option key={t} value={t}>{t.replace(/_/g," ")}</option>)}
          </select>
          <input style={styles.input} placeholder="Threshold (optional)" type="number" step="any"
            value={form.threshold} onChange={(e) => setForm({ ...form, threshold: e.target.value })} />
          <input style={styles.input} placeholder="Message (optional)"
            value={form.message} onChange={(e) => setForm({ ...form, message: e.target.value })} />
          {formError && <p style={{ ...styles.error, gridColumn:"1/-1" }}>{formError}</p>}
          <button style={styles.btn} type="submit" disabled={createMutation.isPending}>
            {createMutation.isPending ? "Creating…" : "Create Alert"}
          </button>
        </form>
      </div>

      {/* Alert list */}
      <div style={{ marginTop: 24 }}>
        {isLoading && <p style={styles.muted}>Loading…</p>}
        {!isLoading && !alerts?.length && <p style={styles.muted}>No alerts configured</p>}
        {alerts?.map((alert) => (
          <div key={alert.id} style={{ ...styles.alertRow, opacity: alert.active ? 1 : 0.5 }}>
            <div>
              <span style={styles.ticker}>{alert.ticker}</span>
              <span style={styles.typeBadge}>{alert.alert_type.replace(/_/g," ")}</span>
              {alert.threshold != null && <span style={styles.muted}> @ {alert.threshold}</span>}
              {alert.message && <p style={styles.alertMsg}>{alert.message}</p>}
              {alert.triggered_at && <p style={{ ...styles.muted, fontSize:12 }}>Triggered: {new Date(alert.triggered_at).toLocaleString()}</p>}
            </div>
            <div style={styles.alertActions}>
              <button style={styles.toggleBtn}
                onClick={() => toggleMutation.mutate({ id: alert.id, active: !alert.active })}>
                {alert.active ? "Pause" : "Resume"}
              </button>
              <button style={styles.deleteBtn}
                onClick={() => deleteMutation.mutate(alert.id)}>
                Delete
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

const styles = {
  title:       { fontSize:22, fontWeight:700, marginBottom:24 },
  card:        { background:"var(--surface)", border:"1px solid var(--border)", borderRadius:10, padding:20 },
  formGrid:    { display:"grid", gridTemplateColumns:"1fr 1fr", gap:10 },
  input:       { padding:"8px 12px", background:"var(--bg)", border:"1px solid var(--border)", borderRadius:6, color:"var(--text)", fontSize:13 },
  btn:         { gridColumn:"1/-1", padding:"9px 0", background:"var(--accent)", border:"none", borderRadius:6, color:"#fff", fontWeight:600 },
  error:       { color:"var(--red)", fontSize:13 },
  alertRow:    { display:"flex", justifyContent:"space-between", alignItems:"flex-start", background:"var(--surface)", border:"1px solid var(--border)", borderRadius:10, padding:16, marginBottom:10 },
  ticker:      { fontWeight:700, fontSize:15, marginRight:8 },
  typeBadge:   { background:"rgba(102,126,234,0.15)", color:"var(--accent)", borderRadius:4, padding:"2px 8px", fontSize:12 },
  alertMsg:    { color:"var(--muted)", fontSize:13, marginTop:4 },
  alertActions:{ display:"flex", gap:8, flexShrink:0, marginLeft:16 },
  toggleBtn:   { padding:"6px 12px", background:"none", border:"1px solid var(--border)", borderRadius:6, color:"var(--text)", fontSize:13 },
  deleteBtn:   { padding:"6px 12px", background:"none", border:"1px solid var(--red)", borderRadius:6, color:"var(--red)", fontSize:13 },
  muted:       { color:"var(--muted)" },
};
