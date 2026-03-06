import React from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth.js";

const NAV = [
  { to: "/portfolio",       label: "Portfolio" },
  { to: "/recommendations", label: "Recommendations" },
  { to: "/market",          label: "Market" },
  { to: "/performance",     label: "Performance" },
  { to: "/backtest",        label: "Backtest" },
  { to: "/alerts",          label: "Alerts" },
];

export default function DashboardLayout() {
  const { logout } = useAuth();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate("/login");
  }

  return (
    <div style={styles.shell}>
      <aside style={styles.sidebar}>
        <div style={styles.logo}>📈 TradingBot</div>
        <nav style={styles.nav}>
          {NAV.map(({ to, label }) => (
            <NavLink
              key={to}
              to={to}
              style={({ isActive }) => ({ ...styles.link, ...(isActive ? styles.active : {}) })}
            >
              {label}
            </NavLink>
          ))}
        </nav>
        <button style={styles.logout} onClick={handleLogout}>Sign out</button>
      </aside>
      <main style={styles.main}>
        <Outlet />
      </main>
    </div>
  );
}

const styles = {
  shell:   { display:"flex", height:"100vh", overflow:"hidden" },
  sidebar: { width:220, background:"var(--surface)", borderRight:"1px solid var(--border)", display:"flex", flexDirection:"column", padding:24 },
  logo:    { fontSize:18, fontWeight:700, marginBottom:32 },
  nav:     { display:"flex", flexDirection:"column", gap:4, flex:1 },
  link:    { padding:"8px 12px", borderRadius:8, color:"var(--muted)", fontWeight:500 },
  active:  { background:"rgba(102,126,234,0.15)", color:"var(--accent)" },
  logout:  { background:"none", border:"1px solid var(--border)", borderRadius:8, color:"var(--muted)", padding:"8px 12px", marginTop:16 },
  main:    { flex:1, overflow:"auto", padding:32 },
};
