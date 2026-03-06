/**
 * Phase 2 Sprint 2 — Performance & P&L Page
 * Shows equity curve chart, portfolio-level recommendation stats,
 * per-symbol breakdown, and a rebalance trigger panel.
 */

import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine,
} from "recharts";
import {
  getPerformance, getEquity, getSymbolEquity, getRebalancePlan, executeRebalance,
} from "../services/api.js";

// ── Equity Chart ─────────────────────────────────────────────────────────────

function EquityChart({ symbol, days }) {
  const fetchFn = symbol ? () => getSymbolEquity(symbol, days) : () => getEquity(days);

  const { data, isLoading } = useQuery({
    queryKey: ["equity", symbol ?? "portfolio", days],
    queryFn: fetchFn,
    staleTime: 120_000,
  });

  if (isLoading) return <div style={styles.chartPlaceholder}>Loading chart…</div>;
  const curve = data?.equity_curve ?? [];
  if (!curve.length) return <div style={styles.chartPlaceholder}>No equity data yet.</div>;

  const base    = curve[0]?.equity || 100_000;
  const last    = curve[curve.length - 1]?.equity || base;
  const pct     = ((last - base) / base * 100).toFixed(2);
  const isGreen = last >= base;

  return (
    <div style={styles.chartWrap}>
      <div style={styles.chartHeader}>
        <span style={styles.chartTitle}>{symbol ?? "Portfolio"} Equity</span>
        <span style={{ color: isGreen ? "#48c78e" : "#f14668", fontWeight: 600 }}>
          {isGreen ? "+" : ""}{pct}%
        </span>
      </div>
      <ResponsiveContainer width="100%" height={220}>
        <LineChart data={curve} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 10, fill: "var(--muted)" }}
            tickFormatter={(v) => v?.slice(5)}
          />
          <YAxis
            tick={{ fontSize: 10, fill: "var(--muted)" }}
            tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`}
            width={52}
          />
          <Tooltip
            formatter={(v) => [`$${v.toLocaleString()}`, "Equity"]}
            contentStyle={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 8 }}
          />
          <ReferenceLine y={base} stroke="var(--muted)" strokeDasharray="4 4" />
          <Line
            type="monotone"
            dataKey="equity"
            stroke={isGreen ? "#48c78e" : "#f14668"}
            dot={false}
            strokeWidth={2}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

// ── Rebalance Panel ───────────────────────────────────────────────────────────

function RebalancePanel() {
  const queryClient = useQueryClient();
  const [showPlan, setShowPlan] = useState(false);

  const { data: plan, isLoading: planLoading } = useQuery({
    queryKey: ["rebalancePlan"],
    queryFn: getRebalancePlan,
    enabled: showPlan,
    staleTime: 30_000,
  });

  const executeMut = useMutation({
    mutationFn: executeRebalance,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["rebalancePlan"] }),
  });

  return (
    <div style={styles.card}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <h3 style={styles.cardTitle}>Portfolio Rebalancer</h3>
        <button style={styles.btnSecondary} onClick={() => setShowPlan(!showPlan)}>
          {showPlan ? "Hide Plan" : "View Plan"}
        </button>
      </div>

      {showPlan && (
        <>
          {planLoading ? (
            <p style={{ color: "var(--muted)" }}>Computing plan…</p>
          ) : plan ? (
            <>
              <div style={styles.statRow}>
                <div style={styles.stat}>
                  <div style={styles.statVal}>{plan.symbol_count ?? "—"}</div>
                  <div style={styles.statLabel}>Symbols</div>
                </div>
                <div style={styles.stat}>
                  <div style={styles.statVal}>{plan.invested_pct ? `${(plan.invested_pct * 100).toFixed(0)}%` : "80%"}</div>
                  <div style={styles.statLabel}>Invested</div>
                </div>
                <div style={styles.stat}>
                  <div style={styles.statVal}>{plan.cash_buffer_pct ? `${(plan.cash_buffer_pct * 100).toFixed(0)}%` : "20%"}</div>
                  <div style={styles.statLabel}>Cash Buffer</div>
                </div>
              </div>

              {plan.target_weights && (
                <div style={{ marginBottom: 16 }}>
                  <div style={styles.tableHeader}>Target Weights</div>
                  {Object.entries(plan.target_weights).map(([ticker, weight]) => (
                    <div key={ticker} style={styles.weightRow}>
                      <span style={{ fontWeight: 600 }}>{ticker}</span>
                      <div style={styles.weightBarWrap}>
                        <div style={{ ...styles.weightBar, width: `${weight * 100 * 4}%` }} />
                      </div>
                      <span style={{ color: "var(--muted)", fontSize: 12 }}>{(weight * 100).toFixed(1)}%</span>
                    </div>
                  ))}
                </div>
              )}

              <p style={{ color: "var(--muted)", fontSize: 12, marginBottom: 12 }}>
                Paper trading only. The bot will execute these orders on the next scheduler run.
              </p>
              <button
                style={executeMut.isPending ? styles.btnDisabled : styles.btnDanger}
                disabled={executeMut.isPending}
                onClick={() => executeMut.mutate()}
              >
                {executeMut.isPending ? "Queuing…" : "Execute Rebalance (Paper)"}
              </button>
              {executeMut.isSuccess && (
                <p style={{ color: "#48c78e", marginTop: 8, fontSize: 13 }}>
                  Rebalance queued successfully.
                </p>
              )}
              {executeMut.isError && (
                <p style={{ color: "#f14668", marginTop: 8, fontSize: 13 }}>
                  Failed to queue rebalance.
                </p>
              )}
            </>
          ) : (
            <p style={{ color: "var(--muted)" }}>No rebalance plan available.</p>
          )}
        </>
      )}
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

const DAY_OPTIONS = [30, 60, 90, 180];

export default function PerformancePage() {
  const [days, setDays]       = useState(90);
  const [symbol, setSymbol]   = useState(null);

  const { data: perfData, isLoading: perfLoading } = useQuery({
    queryKey: ["performance"],
    queryFn: getPerformance,
    staleTime: 60_000,
  });

  const symbols = perfData?.symbols ?? [];

  return (
    <div>
      <h2 style={styles.heading}>Performance & P&amp;L</h2>

      {/* ── Controls ── */}
      <div style={{ display: "flex", gap: 8, marginBottom: 24, alignItems: "center" }}>
        <span style={{ color: "var(--muted)", fontSize: 13 }}>Period:</span>
        {DAY_OPTIONS.map(d => (
          <button
            key={d}
            style={{ ...styles.chipBtn, ...(days === d ? styles.chipBtnActive : {}) }}
            onClick={() => setDays(d)}
          >{d}d</button>
        ))}
        {symbol && (
          <button style={{ ...styles.chipBtn, marginLeft: 16 }} onClick={() => setSymbol(null)}>
            ✕ {symbol}
          </button>
        )}
      </div>

      {/* ── Equity Charts ── */}
      <div style={styles.chartGrid}>
        <EquityChart symbol={null} days={days} />
        {symbol && <EquityChart symbol={symbol} days={days} />}
      </div>

      {/* ── Recommendation Stats ── */}
      {perfLoading ? null : perfData && (
        <div style={{ ...styles.card, marginTop: 24 }}>
          <h3 style={styles.cardTitle}>Recommendation Quality</h3>
          <div style={styles.statRow}>
            {[
              ["Total",    perfData.recommendations?.total],
              ["Buys",     perfData.recommendations?.buy_count],
              ["Sells",    perfData.recommendations?.sell_count],
              ["Holds",    perfData.recommendations?.hold_count],
              ["Claude",   perfData.recommendations?.claude_count],
              ["Fallback", perfData.recommendations?.fallback_count],
              ["Avg Conf", perfData.recommendations?.avg_confidence
                ? `${(perfData.recommendations.avg_confidence * 100).toFixed(1)}%`
                : "—"],
            ].map(([label, val]) => (
              <div key={label} style={styles.stat}>
                <div style={styles.statVal}>{val ?? "—"}</div>
                <div style={styles.statLabel}>{label}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Per-symbol Table ── */}
      {symbols.length > 0 && (
        <div style={{ ...styles.card, marginTop: 24 }}>
          <h3 style={styles.cardTitle}>Per-Symbol Breakdown</h3>
          <div style={styles.tableWrap}>
            <table style={styles.table}>
              <thead>
                <tr>
                  {["Symbol", "Recs", "Buys", "Sells", "Holds", "Avg Conf", "Avg Score"].map(h => (
                    <th key={h} style={styles.th}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {symbols.map((s) => (
                  <tr
                    key={s.ticker}
                    style={{ ...styles.tr, cursor: "pointer" }}
                    onClick={() => setSymbol(s.ticker)}
                  >
                    <td style={{ ...styles.td, fontWeight: 600, color: "var(--accent)" }}>{s.ticker}</td>
                    <td style={styles.td}>{s.rec_count}</td>
                    <td style={styles.td}>{s.buy_count}</td>
                    <td style={styles.td}>{s.sell_count}</td>
                    <td style={styles.td}>{s.hold_count}</td>
                    <td style={styles.td}>{s.avg_confidence ? `${(s.avg_confidence * 100).toFixed(1)}%` : "—"}</td>
                    <td style={styles.td}>{s.avg_composite ? Number(s.avg_composite).toFixed(1) : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p style={{ color: "var(--muted)", fontSize: 11, marginTop: 8 }}>Click a row to view its equity chart.</p>
        </div>
      )}

      {/* ── Rebalancer ── */}
      <div style={{ marginTop: 24 }}>
        <RebalancePanel />
      </div>
    </div>
  );
}

const styles = {
  heading:       { fontSize: 24, fontWeight: 700, marginBottom: 8 },
  chipBtn:       { padding: "4px 12px", borderRadius: 16, border: "1px solid var(--border)", background: "var(--surface)", color: "var(--muted)", cursor: "pointer", fontSize: 13 },
  chipBtnActive: { background: "rgba(102,126,234,0.15)", borderColor: "var(--accent)", color: "var(--accent)" },
  chartGrid:     { display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(340px, 1fr))", gap: 16 },
  chartWrap:     { background: "var(--surface)", borderRadius: 12, padding: 20 },
  chartPlaceholder: { background: "var(--surface)", borderRadius: 12, padding: 20, color: "var(--muted)", textAlign: "center", height: 260, display: "flex", alignItems: "center", justifyContent: "center" },
  chartHeader:   { display: "flex", justifyContent: "space-between", marginBottom: 12 },
  chartTitle:    { fontWeight: 600, fontSize: 15 },
  card:          { background: "var(--surface)", borderRadius: 12, padding: 24 },
  cardTitle:     { fontSize: 18, fontWeight: 600, marginBottom: 20 },
  statRow:       { display: "flex", gap: 12, flexWrap: "wrap", marginBottom: 16 },
  stat:          { background: "var(--bg)", borderRadius: 8, padding: "10px 16px", minWidth: 80, textAlign: "center" },
  statVal:       { fontSize: 20, fontWeight: 700 },
  statLabel:     { fontSize: 11, color: "var(--muted)", marginTop: 2 },
  tableHeader:   { fontWeight: 600, marginBottom: 10, fontSize: 13 },
  weightRow:     { display: "flex", alignItems: "center", gap: 12, marginBottom: 6 },
  weightBarWrap: { flex: 1, height: 8, background: "var(--border)", borderRadius: 4, overflow: "hidden" },
  weightBar:     { height: "100%", background: "var(--accent)", borderRadius: 4, transition: "width 0.4s" },
  tableWrap:     { overflowX: "auto" },
  table:         { width: "100%", borderCollapse: "collapse" },
  th:            { textAlign: "left", padding: "8px 12px", borderBottom: "1px solid var(--border)", fontSize: 12, color: "var(--muted)", fontWeight: 600 },
  tr:            { borderBottom: "1px solid var(--border)" },
  td:            { padding: "10px 12px", fontSize: 13 },
  btnSecondary:  { padding: "6px 14px", borderRadius: 8, border: "1px solid var(--border)", background: "none", color: "var(--fg)", cursor: "pointer", fontSize: 13 },
  btnDanger:     { padding: "8px 16px", borderRadius: 8, border: "none", background: "#f14668", color: "#fff", cursor: "pointer", fontWeight: 600 },
  btnDisabled:   { padding: "8px 16px", borderRadius: 8, border: "none", background: "var(--border)", color: "var(--muted)", cursor: "not-allowed", fontWeight: 600 },
};
