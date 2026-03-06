import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth.js";

export default function LoginPage() {
  const { login, error, loading } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ username: "", password: "" });

  async function handleSubmit(e) {
    e.preventDefault();
    const ok = await login(form.username, form.password);
    if (ok) navigate("/portfolio");
  }

  return (
    <div style={styles.wrap}>
      <div style={styles.card}>
        <h1 style={styles.title}>Trading Bot</h1>
        <p style={styles.sub}>Sign in to your dashboard</p>
        <form onSubmit={handleSubmit} style={styles.form}>
          <input
            style={styles.input}
            placeholder="Username"
            value={form.username}
            onChange={(e) => setForm({ ...form, username: e.target.value })}
            required
          />
          <input
            style={styles.input}
            type="password"
            placeholder="Password"
            value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })}
            required
          />
          {error && <p style={styles.error}>{error}</p>}
          <button style={styles.btn} type="submit" disabled={loading}>
            {loading ? "Signing in…" : "Sign in"}
          </button>
        </form>
      </div>
    </div>
  );
}

const styles = {
  wrap:  { display:"flex", alignItems:"center", justifyContent:"center", height:"100vh", background:"var(--bg)" },
  card:  { background:"var(--surface)", border:"1px solid var(--border)", borderRadius:12, padding:40, width:360 },
  title: { fontSize:24, fontWeight:700, marginBottom:4 },
  sub:   { color:"var(--muted)", marginBottom:24 },
  form:  { display:"flex", flexDirection:"column", gap:12 },
  input: { padding:"10px 14px", background:"var(--bg)", border:"1px solid var(--border)", borderRadius:8, color:"var(--text)", fontSize:14 },
  error: { color:"var(--red)", fontSize:13 },
  btn:   { padding:"10px 0", background:"var(--accent)", border:"none", borderRadius:8, color:"#fff", fontWeight:600, fontSize:15 },
};
