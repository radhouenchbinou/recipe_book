import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getSettings, updateSettings } from "../services/api.js";
import { useNotifications } from "../hooks/useNotifications.js";

export default function SettingsPage() {
  const qc = useQueryClient();
  const { notify } = useNotifications();
  const { data: settings, isLoading } = useQuery({
    queryKey: ["settings"],
    queryFn: getSettings,
  });

  const mutation = useMutation({
    mutationFn: updateSettings,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["settings"] });
      notify("Settings saved", "success");
    },
    onError: (err) => notify(err.response?.data?.error ?? "Save failed", "error"),
  });

  const [form, setForm] = useState(null);
  const current = form ?? settings ?? {};

  function handleChange(e) {
    const { name, value, type, checked } = e.target;
    setForm((prev) => ({ ...current, ...prev, [name]: type === "checkbox" ? checked : value }));
  }

  function handleSubmit(e) {
    e.preventDefault();
    mutation.mutate(form);
  }

  if (isLoading) return <p style={{ color: "var(--muted)" }}>Loading…</p>;

  return (
    <div>
      <h1 style={styles.heading}>Settings</h1>
      <form onSubmit={handleSubmit} style={styles.form}>
        <section style={styles.section}>
          <h2 style={styles.sectionTitle}>Notifications</h2>

          <label style={styles.checkRow}>
            <input type="checkbox" name="notify_slack" checked={!!current.notify_slack} onChange={handleChange} />
            Slack notifications
          </label>
          {current.notify_slack && (
            <input
              style={styles.input} type="url" name="slack_webhook"
              placeholder="https://hooks.slack.com/..." value={current.slack_webhook ?? ""}
              onChange={handleChange}
            />
          )}

          <label style={styles.checkRow}>
            <input type="checkbox" name="notify_email" checked={!!current.notify_email} onChange={handleChange} />
            Email notifications
          </label>
          {current.notify_email && (
            <input
              style={styles.input} type="email" name="email_addr"
              placeholder="you@example.com" value={current.email_addr ?? ""}
              onChange={handleChange}
            />
          )}

          <label style={styles.checkRow}>
            <input type="checkbox" name="notify_sms" checked={!!current.notify_sms} onChange={handleChange} />
            SMS notifications
          </label>
          {current.notify_sms && (
            <input
              style={styles.input} type="tel" name="phone_number"
              placeholder="+1234567890" value={current.phone_number ?? ""}
              onChange={handleChange}
            />
          )}
        </section>

        <section style={styles.section}>
          <h2 style={styles.sectionTitle}>Risk Tolerance</h2>
          <select style={styles.select} name="risk_tolerance" value={current.risk_tolerance ?? "medium"} onChange={handleChange}>
            <option value="low">Low — conservative, fewer trades</option>
            <option value="medium">Medium — balanced</option>
            <option value="high">High — aggressive, more trades</option>
          </select>
        </section>

        <button style={styles.btn} type="submit" disabled={mutation.isPending}>
          {mutation.isPending ? "Saving…" : "Save settings"}
        </button>
      </form>
    </div>
  );
}

const styles = {
  heading:      { fontSize: 24, fontWeight: 700, marginBottom: 24 },
  form:         { display: "flex", flexDirection: "column", gap: 24, maxWidth: 520 },
  section:      { display: "flex", flexDirection: "column", gap: 12 },
  sectionTitle: { fontSize: 16, fontWeight: 600, color: "var(--muted)", marginBottom: 4 },
  checkRow:     { display: "flex", alignItems: "center", gap: 10, fontSize: 14, cursor: "pointer" },
  input:        { background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 8, padding: "8px 12px", color: "var(--text)", fontSize: 14 },
  select:       { background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 8, padding: "8px 12px", color: "var(--text)", fontSize: 14 },
  btn:          { alignSelf: "flex-start", background: "var(--accent)", color: "#fff", border: "none", borderRadius: 8, padding: "10px 24px", cursor: "pointer", fontWeight: 600 },
};
