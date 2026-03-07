import React from "react";
import { useQuery } from "@tanstack/react-query";
import { getPortfolio, getPositions } from "../services/api.js";

function Stat({ label, value, positive }) {
  const color = positive === undefined ? "var(--text)" : positive ? "var(--green)" : "var(--red)";
  return (
    <div style={styles.stat}>
      <span style={styles.statLabel}>{label}</span>
      <span style={{ ...styles.statValue, color }}>{value}</span>
    </div>
  );
}

function fmt(n, decimals = 2) { return n == null ? "—" : Number(n).toLocaleString("en-US", { minimumFractionDigits: decimals, maximumFractionDigits: decimals }); }
function fmtUSD(n) { return n == null ? "—" : `$${fmt(n)}`; }
function fmtPct(n) { return n == null ? "—" : `${n >= 0 ? "+" : ""}${fmt(n)}%`; }

export default function PortfolioPage() {
  const portfolio = useQuery({ queryKey: ["portfolio"], queryFn: getPortfolio, refetchInterval: 30_000 });
  const positions = useQuery({ queryKey: ["positions"], queryFn: getPositions, refetchInterval: 30_000 });

  const acct = portfolio.data;
  const isPaper = acct?.is_paper;

  return (
    <div>
      <div style={styles.header}>
        <h2 style={styles.title}>Portfolio Overview</h2>
        {isPaper && <span style={styles.badge}>Paper Trading</span>}
      </div>

      {portfolio.isLoading ? <p style={styles.muted}>Loading…</p> : portfolio.isError ? (
        <p style={styles.error}>Could not load portfolio — is the API running?</p>
      ) : (
        <div style={styles.statsGrid}>
          <Stat label="Portfolio Value" value={fmtUSD(acct.portfolio_value)} />
          <Stat label="Equity"          value={fmtUSD(acct.equity)} />
          <Stat label="Cash"            value={fmtUSD(acct.cash)} />
          <Stat label="Buying Power"    value={fmtUSD(acct.buying_power)} />
          <Stat label="Day P&L"         value={fmtUSD(acct.day_pl)}      positive={acct.day_pl >= 0} />
          <Stat label="Day P&L %"       value={fmtPct(acct.day_pl_pct)}  positive={acct.day_pl_pct >= 0} />
        </div>
      )}

      <h3 style={{ marginTop: 32, marginBottom: 16, fontSize: 16 }}>Open Positions</h3>

      {positions.isLoading ? <p style={styles.muted}>Loading…</p> : positions.isError ? (
        <p style={styles.error}>Could not load positions</p>
      ) : !positions.data?.length ? (
        <p style={styles.muted}>No open positions</p>
      ) : (
        <table style={styles.table}>
          <thead>
            <tr>{["Symbol","Qty","Current Price","Market Value","Unrealized P&L","P&L %","Side"].map(h => (
              <th key={h} style={styles.th}>{h}</th>
            ))}</tr>
          </thead>
          <tbody>
            {positions.data.map((p) => (
              <tr key={p.symbol} style={styles.tr}>
                <td style={{ ...styles.td, fontWeight: 600 }}>{p.symbol}</td>
                <td style={styles.td}>{fmt(p.qty, 0)}</td>
                <td style={styles.td}>{fmtUSD(p.current_price)}</td>
                <td style={styles.td}>{fmtUSD(p.market_value)}</td>
                <td style={{ ...styles.td, color: p.unrealized_pl >= 0 ? "var(--green)" : "var(--red)" }}>
                  {fmtUSD(p.unrealized_pl)}
                </td>
                <td style={{ ...styles.td, color: p.unrealized_pct >= 0 ? "var(--green)" : "var(--red)" }}>
                  {fmtPct(p.unrealized_pct)}
                </td>
                <td style={styles.td}>{p.side}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

const styles = {
  header:     { display:"flex", alignItems:"center", gap:12, marginBottom:24 },
  title:      { fontSize:22, fontWeight:700 },
  badge:      { background:"rgba(246,224,94,0.15)", color:"var(--yellow)", border:"1px solid var(--yellow)", borderRadius:6, padding:"2px 8px", fontSize:12 },
  statsGrid:  { display:"grid", gridTemplateColumns:"repeat(auto-fill, minmax(160px,1fr))", gap:16 },
  stat:       { background:"var(--surface)", border:"1px solid var(--border)", borderRadius:10, padding:16 },
  statLabel:  { display:"block", color:"var(--muted)", fontSize:12, marginBottom:6 },
  statValue:  { display:"block", fontSize:20, fontWeight:700 },
  table:      { width:"100%", borderCollapse:"collapse" },
  th:         { padding:"10px 12px", textAlign:"left", color:"var(--muted)", fontSize:12, borderBottom:"1px solid var(--border)" },
  td:         { padding:"10px 12px", borderBottom:"1px solid var(--border)" },
  tr:         { transition:"background 0.1s" },
  muted:      { color:"var(--muted)" },
  error:      { color:"var(--red)" },
};
