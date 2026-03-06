/**
 * Phase 2 Sprint 3 — Risk & Optimization Page
 * Displays optimized target weights, VaR / CVaR, beta, and
 * a colour-coded correlation heatmap.
 */

import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getOptimizedWeights, getPortfolioRisk, getDrift } from "../services/api.js";

// ── Helpers ────────────────────────────────────────────────────────────────

function pctFmt(v, decimals = 2) {
  if (v == null) return "—";
  return `${Number(v).toFixed(decimals)}%`;
}

function numFmt(v, decimals = 4) {
  if (v == null) return "—";
  return Number(v).toFixed(decimals);
}

/** Map a correlation value −1..+1 to a red–white–green colour. */
function corrColor(v) {
  if (v == null) return "var(--surface)";
  const t = (v + 1) / 2;   // 0..1
  const r = Math.round(241 * (1 - t) + 72 * t);
  const g = Math.round(70  * (1 - t) + 199 * t);
  const b = Math.round(104 * (1 - t) + 142 * t);
  return `rgba(${r},${g},${b},0.4)`;
}

// ── Sub-components ─────────────────────────────────────────────────────────

function OptimizePanel() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["optimizeWeights"],
    queryFn:  getOptimizedWeights,
    staleTime: 60_000,
  });

  if (isLoading) return <p style={{ color: "var(--muted)" }}>Computing weights…</p>;
  if (isError)   return <p style={{ color: "#f14668" }}>Failed to load optimizer.</p>;

  const weights = data?.weights ?? [];
  return (
    <div style={s.card}>
      <h3 style={s.cardTitle}>Optimized Target Weights</h3>
      <div style={{ color: "var(--muted)", fontSize: 12, marginBottom: 16 }}>
        Score ÷ (1 + vol_penalty × σ) — higher volatility = lower weight for same score.
        Invested: <strong>{pctFmt((data?.invested_pct ?? 0) * 100, 1)}</strong> ·
        Cash buffer: <strong>{pctFmt((data?.cash_pct ?? 0) * 100, 1)}</strong>
      </div>

      {weights.length === 0 ? (
        <p style={{ color: "var(--muted)" }}>No bullish symbols available.</p>
      ) : (
        weights.map((w) => (
          <div key={w.ticker} style={s.weightRow}>
            <span style={s.tickerLabel}>{w.ticker}</span>
            <div style={s.barOuter}>
              <div style={{ ...s.barInner, width: `${w.target_weight_pct * 4}%` }} />
            </div>
            <span style={s.weightNum}>{pctFmt(w.target_weight_pct, 1)}</span>
            <span style={s.volBadge}>σ {pctFmt((w.volatility ?? 0) * 100, 1)}</span>
            <span style={s.scoreBadge}>{numFmt(w.composite_score, 1)}</span>
          </div>
        ))
      )}
      {data?.skipped?.length > 0 && (
        <p style={{ color: "var(--muted)", fontSize: 11, marginTop: 12 }}>
          Excluded (bearish): {data.skipped.join(", ")}
        </p>
      )}
    </div>
  );
}

function DriftPanel() {
  const [threshold, setThreshold] = useState(0.03);

  const { data, isLoading } = useQuery({
    queryKey: ["drift", threshold],
    queryFn:  () => getDrift(threshold),
    staleTime: 30_000,
  });

  const entries = data?.entries ?? [];

  return (
    <div style={s.card}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <h3 style={s.cardTitle}>Drift Detection</h3>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{ fontSize: 12, color: "var(--muted)" }}>Threshold</span>
          <select
            style={s.select}
            value={threshold}
            onChange={(e) => setThreshold(Number(e.target.value))}
          >
            {[0.01, 0.02, 0.03, 0.05].map(v => (
              <option key={v} value={v}>{(v * 100).toFixed(0)}%</option>
            ))}
          </select>
        </div>
      </div>

      {isLoading ? (
        <p style={{ color: "var(--muted)" }}>Analysing drift…</p>
      ) : entries.length === 0 ? (
        <p style={{ color: "var(--muted)" }}>No positions to analyse.</p>
      ) : (
        <div style={s.tableWrap}>
          <table style={s.table}>
            <thead>
              <tr>
                {["Symbol", "Current", "Target", "Drift", "Action"].map(h => (
                  <th key={h} style={s.th}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {entries.map((e) => (
                <tr key={e.ticker} style={s.tr}>
                  <td style={{ ...s.td, fontWeight: 600 }}>{e.ticker}</td>
                  <td style={s.td}>{pctFmt((e.current_weight ?? 0) * 100, 1)}</td>
                  <td style={s.td}>{pctFmt((e.target_weight  ?? 0) * 100, 1)}</td>
                  <td style={{ ...s.td, color: e.drift > 0 ? "#f14668" : "#48c78e" }}>
                    {e.drift > 0 ? "+" : ""}{pctFmt((e.drift ?? 0) * 100, 1)}
                  </td>
                  <td style={s.td}>
                    <span style={{
                      background: e.action === "buy" ? "rgba(72,199,142,0.15)" :
                                  e.action === "sell" ? "rgba(241,70,104,0.15)" :
                                  "rgba(100,100,120,0.15)",
                      color: e.action === "buy" ? "#48c78e" :
                             e.action === "sell" ? "#f14668" : "var(--muted)",
                      borderRadius: 6, padding: "2px 8px", fontSize: 12, fontWeight: 600,
                    }}>
                      {e.action?.toUpperCase()}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {data?.needs_rebalance && (
        <p style={{ color: "#f14668", fontSize: 12, marginTop: 8 }}>
          {data.rebalance_count} symbol(s) need rebalancing.
        </p>
      )}
    </div>
  );
}

function RiskPanel() {
  const [days, setDays] = useState(252);
  const [selected, setSelected] = useState(null);

  const { data, isLoading, isError } = useQuery({
    queryKey: ["portfolioRisk", days],
    queryFn:  () => getPortfolioRisk({ days }),
    staleTime: 120_000,
  });

  const symbols = data?.symbols ?? [];
  const tickers = data?.correlation_matrix?.tickers ?? [];
  const matrix  = data?.correlation_matrix?.matrix  ?? {};

  return (
    <div>
      <div style={s.card}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
          <h3 style={s.cardTitle}>Risk Metrics (VaR / Beta)</h3>
          <select style={s.select} value={days} onChange={(e) => setDays(Number(e.target.value))}>
            {[63, 126, 252].map(d => (
              <option key={d} value={d}>{d === 63 ? "3M" : d === 126 ? "6M" : "1Y"}</option>
            ))}
          </select>
        </div>

        {isLoading ? (
          <p style={{ color: "var(--muted)" }}>Loading risk data…</p>
        ) : isError ? (
          <p style={{ color: "#f14668" }}>Failed to load risk metrics.</p>
        ) : (
          <div style={s.tableWrap}>
            <table style={s.table}>
              <thead>
                <tr>
                  {["Symbol", "1-Day VaR (95%)", "CVaR (95%)", "Beta", "Correlation", "R²"].map(h => (
                    <th key={h} style={s.th}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {symbols.map((sym) => (
                  <tr
                    key={sym.ticker}
                    style={{ ...s.tr, cursor: "pointer" }}
                    onClick={() => setSelected(selected === sym.ticker ? null : sym.ticker)}
                  >
                    <td style={{ ...s.td, fontWeight: 600, color: "var(--accent)" }}>{sym.ticker}</td>
                    <td style={{ ...s.td, color: "#f14668" }}>{pctFmt(sym.var_pct)}</td>
                    <td style={{ ...s.td, color: "#f14668" }}>{pctFmt(sym.cvar_pct)}</td>
                    <td style={s.td}>{numFmt(sym.beta)}</td>
                    <td style={s.td}>{numFmt(sym.correlation)}</td>
                    <td style={s.td}>{numFmt(sym.r_squared)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Correlation Heatmap */}
      {tickers.length > 1 && (
        <div style={{ ...s.card, marginTop: 24 }}>
          <h3 style={s.cardTitle}>Correlation Matrix</h3>
          <div style={{ overflowX: "auto" }}>
            <table style={{ ...s.table, width: "auto" }}>
              <thead>
                <tr>
                  <th style={s.th}></th>
                  {tickers.map(t => <th key={t} style={s.th}>{t}</th>)}
                </tr>
              </thead>
              <tbody>
                {tickers.map(t1 => (
                  <tr key={t1}>
                    <td style={{ ...s.td, fontWeight: 600 }}>{t1}</td>
                    {tickers.map(t2 => {
                      const v = matrix[t1]?.[t2];
                      return (
                        <td
                          key={t2}
                          style={{ ...s.td, background: corrColor(v), textAlign: "center", minWidth: 56 }}
                          title={`${t1}/${t2}: ${numFmt(v)}`}
                        >
                          {numFmt(v, 2)}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p style={{ fontSize: 11, color: "var(--muted)", marginTop: 8 }}>
            Green = positive correlation · Red = negative correlation
          </p>
        </div>
      )}
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────

export default function RiskPage() {
  return (
    <div>
      <h2 style={s.heading}>Risk &amp; Optimization</h2>
      <p style={{ color: "var(--muted)", marginBottom: 24 }}>
        Volatility-dampened target weights, drift detection, and advanced risk metrics
        (Value-at-Risk, CVaR, beta, correlation).
      </p>

      <div style={s.grid2}>
        <OptimizePanel />
        <DriftPanel />
      </div>
      <div style={{ marginTop: 24 }}>
        <RiskPanel />
      </div>
    </div>
  );
}

const s = {
  heading:    { fontSize: 24, fontWeight: 700, marginBottom: 8 },
  grid2:      { display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(340px, 1fr))", gap: 16 },
  card:       { background: "var(--surface)", borderRadius: 12, padding: 24 },
  cardTitle:  { fontSize: 18, fontWeight: 600, marginBottom: 16 },
  weightRow:  { display: "flex", alignItems: "center", gap: 10, marginBottom: 8 },
  tickerLabel:{ width: 48, fontWeight: 700, fontSize: 13 },
  barOuter:   { flex: 1, height: 10, background: "var(--border)", borderRadius: 5, overflow: "hidden" },
  barInner:   { height: "100%", background: "var(--accent)", borderRadius: 5, transition: "width 0.4s" },
  weightNum:  { width: 44, textAlign: "right", fontSize: 13, fontWeight: 600 },
  volBadge:   { background: "rgba(100,100,120,0.2)", borderRadius: 4, padding: "1px 6px", fontSize: 10, color: "var(--muted)" },
  scoreBadge: { background: "rgba(102,126,234,0.15)", borderRadius: 4, padding: "1px 6px", fontSize: 10, color: "var(--accent)" },
  select:     { background: "var(--bg)", border: "1px solid var(--border)", borderRadius: 6, color: "var(--fg)", padding: "4px 8px", fontSize: 12 },
  tableWrap:  { overflowX: "auto" },
  table:      { width: "100%", borderCollapse: "collapse" },
  th:         { textAlign: "left", padding: "8px 12px", borderBottom: "1px solid var(--border)", fontSize: 12, color: "var(--muted)", fontWeight: 600 },
  tr:         { borderBottom: "1px solid var(--border)" },
  td:         { padding: "10px 12px", fontSize: 13 },
};
