import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getRecommendations } from "../services/api.js";

const ACTION_COLOR = { buy: "var(--green)", sell: "var(--red)", hold: "var(--yellow)" };
const SOURCE_LABEL = { claude: "Claude AI", fallback: "Rule-Based" };

function ConfidenceBar({ value }) {
  const pct = Math.round(value * 100);
  const color = pct >= 70 ? "var(--green)" : pct >= 50 ? "var(--yellow)" : "var(--red)";
  return (
    <div style={{ background: "var(--border)", borderRadius: 4, height: 6, width: 100 }}>
      <div style={{ width: `${pct}%`, height: "100%", background: color, borderRadius: 4 }} />
    </div>
  );
}

export default function RecommendationsPage() {
  const [filters, setFilters] = useState({ source: "all", action: "all" });

  const { data, isLoading, isError } = useQuery({
    queryKey: ["recommendations", filters],
    queryFn: () => getRecommendations({ ...filters, limit: 50 }),
    refetchInterval: 60_000,
  });

  function setFilter(key, val) { setFilters((f) => ({ ...f, [key]: val })); }

  return (
    <div>
      <div style={styles.header}>
        <h2 style={styles.title}>Recommendations</h2>
        <div style={styles.filters}>
          {[["source", ["all","claude","fallback"]], ["action", ["all","buy","sell","hold"]]].map(([key, opts]) => (
            <select key={key} style={styles.select} value={filters[key]} onChange={(e) => setFilter(key, e.target.value)}>
              {opts.map((o) => <option key={o} value={o}>{o.charAt(0).toUpperCase() + o.slice(1)}</option>)}
            </select>
          ))}
        </div>
      </div>

      {isLoading && <p style={styles.muted}>Loading…</p>}
      {isError && <p style={styles.error}>Failed to load recommendations</p>}

      <div style={styles.grid}>
        {data?.data?.map((rec) => (
          <div key={rec.id} style={styles.card}>
            <div style={styles.cardTop}>
              <span style={styles.ticker}>{rec.ticker}</span>
              <span style={{ ...styles.actionBadge, background: `${ACTION_COLOR[rec.action]}22`, color: ACTION_COLOR[rec.action] }}>
                {rec.action.toUpperCase()}
              </span>
            </div>
            <div style={styles.confidenceRow}>
              <ConfidenceBar value={rec.confidence} />
              <span style={styles.confText}>{Math.round(rec.confidence * 100)}%</span>
            </div>
            <p style={styles.reasoning}>{rec.reasoning}</p>
            <div style={styles.cardFooter}>
              <span style={styles.sourceBadge}>{SOURCE_LABEL[rec.source] ?? rec.source}</span>
              <span style={styles.timestamp}>{new Date(rec.recommended_at).toLocaleString()}</span>
            </div>
          </div>
        ))}
      </div>

      {data?.data?.length === 0 && <p style={styles.muted}>No recommendations found</p>}
    </div>
  );
}

const styles = {
  header:       { display:"flex", alignItems:"center", justifyContent:"space-between", marginBottom:24 },
  title:        { fontSize:22, fontWeight:700 },
  filters:      { display:"flex", gap:8 },
  select:       { background:"var(--surface)", border:"1px solid var(--border)", color:"var(--text)", padding:"6px 10px", borderRadius:6, fontSize:13 },
  grid:         { display:"grid", gridTemplateColumns:"repeat(auto-fill,minmax(320px,1fr))", gap:16 },
  card:         { background:"var(--surface)", border:"1px solid var(--border)", borderRadius:10, padding:16 },
  cardTop:      { display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:10 },
  ticker:       { fontWeight:700, fontSize:16 },
  actionBadge:  { padding:"3px 10px", borderRadius:6, fontWeight:700, fontSize:13 },
  confidenceRow:{ display:"flex", alignItems:"center", gap:8, marginBottom:10 },
  confText:     { fontSize:13, color:"var(--muted)" },
  reasoning:    { fontSize:13, color:"var(--muted)", lineHeight:1.5, marginBottom:12 },
  cardFooter:   { display:"flex", justifyContent:"space-between", alignItems:"center" },
  sourceBadge:  { fontSize:11, background:"rgba(102,126,234,0.15)", color:"var(--accent)", borderRadius:4, padding:"2px 6px" },
  timestamp:    { fontSize:11, color:"var(--muted)" },
  muted:        { color:"var(--muted)" },
  error:        { color:"var(--red)" },
};
