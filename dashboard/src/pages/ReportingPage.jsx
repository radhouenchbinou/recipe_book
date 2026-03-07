/**
 * Phase 3 Sprint 3 — Reporting Page
 * Three tabs: Trade Log · Realised P&L · Recommendation Accuracy
 * Supports JSON view and direct CSV download via the API.
 */

import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  getReportTrades,
  getReportPnl,
  getReportAccuracy,
  downloadReportCsv,
} from "../services/api.js";

// ── Helpers ────────────────────────────────────────────────────────────────

function fmt(v, decimals = 2) {
  if (v == null) return "—";
  return Number(v).toFixed(decimals);
}

function fmtCurrency(v) {
  if (v == null) return "—";
  const n = Number(v);
  const color = n >= 0 ? "#48c774" : "#f14668";
  return <span style={{ color }}>{n >= 0 ? "+" : ""}${fmt(n)}</span>;
}

function fmtDate(str) {
  if (!str) return "—";
  return new Date(str).toLocaleString(undefined, {
    dateStyle: "short",
    timeStyle: "short",
  });
}

function Badge({ text, colorMap }) {
  const color = colorMap?.[text] ?? "var(--muted)";
  return (
    <span
      style={{
        display: "inline-block",
        padding: "2px 8px",
        borderRadius: 999,
        fontSize: 11,
        fontWeight: 600,
        background: `${color}22`,
        color,
        textTransform: "uppercase",
      }}
    >
      {text}
    </span>
  );
}

const SIDE_COLORS  = { buy: "#48c774", sell: "#f14668" };
const STATUS_COLORS = { filled: "#48c774", rejected: "#f14668", accepted: "#667eea", cancelled: "#888" };

// ── Period selector ─────────────────────────────────────────────────────────

function PeriodSelector({ value, onChange }) {
  const options = [
    { label: "7d",  days: 7  },
    { label: "30d", days: 30 },
    { label: "90d", days: 90 },
    { label: "1y",  days: 365 },
  ];
  return (
    <div style={{ display: "flex", gap: 8 }}>
      {options.map((o) => (
        <button
          key={o.days}
          onClick={() => onChange(o.days)}
          style={{
            ...s.periodBtn,
            ...(value === o.days ? s.periodActive : {}),
          }}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

// ── Trade Log tab ──────────────────────────────────────────────────────────

function TradeLogTab() {
  const [days,   setDays]   = useState(30);
  const [symbol, setSymbol] = useState("");
  const [status, setStatus] = useState("");

  const { data, isLoading, isError } = useQuery({
    queryKey: ["reportTrades", days, symbol, status],
    queryFn:  () => getReportTrades({ days, symbol: symbol || undefined, status: status || undefined }),
    staleTime: 30_000,
  });

  const rows    = data?.rows    ?? [];
  const summary = data?.summary ?? {};

  function handleDownload() {
    downloadReportCsv("trades", { days, symbol: symbol || undefined, status: status || undefined });
  }

  return (
    <div>
      <div style={s.toolbar}>
        <PeriodSelector value={days} onChange={setDays} />
        <input
          style={s.filterInput}
          placeholder="Symbol filter…"
          value={symbol}
          onChange={(e) => setSymbol(e.target.value.toUpperCase())}
        />
        <select
          style={s.filterSelect}
          value={status}
          onChange={(e) => setStatus(e.target.value)}
        >
          <option value="">All statuses</option>
          <option value="filled">filled</option>
          <option value="rejected">rejected</option>
          <option value="accepted">accepted</option>
          <option value="cancelled">cancelled</option>
        </select>
        <button style={s.csvBtn} onClick={handleDownload}>⬇ CSV</button>
      </div>

      {/* Summary pills */}
      <div style={s.summaryRow}>
        {[
          ["Total orders",  summary.total_orders  ?? 0],
          ["Filled buys",   summary.filled_buys   ?? 0],
          ["Filled sells",  summary.filled_sells  ?? 0],
          ["Rejected",      summary.rejected       ?? 0],
        ].map(([label, val]) => (
          <div key={label} style={s.pill}>
            <span style={s.pillLabel}>{label}</span>
            <span style={s.pillVal}>{val}</span>
          </div>
        ))}
      </div>

      {isLoading && <p style={s.muted}>Loading orders…</p>}
      {isError   && <p style={s.err}>Failed to load trade log.</p>}
      {!isLoading && !isError && rows.length === 0 && (
        <p style={s.muted}>No orders for the selected period.</p>
      )}

      {rows.length > 0 && (
        <div style={s.tableWrap}>
          <table style={s.table}>
            <thead>
              <tr>
                {["Date", "Symbol", "Side", "Qty", "Price", "Status", "Source", "Broker"].map((h) => (
                  <th key={h} style={s.th}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id} style={s.tr}>
                  <td style={s.td}>{fmtDate(r.created_at)}</td>
                  <td style={{ ...s.td, fontWeight: 600 }}>{r.symbol}</td>
                  <td style={s.td}><Badge text={r.side}   colorMap={SIDE_COLORS} /></td>
                  <td style={s.td}>{r.qty}</td>
                  <td style={s.td}>{r.filled_price != null ? `$${fmt(r.filled_price)}` : "—"}</td>
                  <td style={s.td}><Badge text={r.status} colorMap={STATUS_COLORS} /></td>
                  <td style={s.td}>{r.source ?? "—"}</td>
                  <td style={{ ...s.td, color: "var(--muted)", fontSize: 12 }}>{r.broker}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ── P&L tab ────────────────────────────────────────────────────────────────

function PnlTab() {
  const [days, setDays] = useState(90);

  const { data, isLoading, isError } = useQuery({
    queryKey: ["reportPnl", days],
    queryFn:  () => getReportPnl({ days }),
    staleTime: 30_000,
  });

  const rows    = data?.rows    ?? [];
  const summary = data?.summary ?? {};

  function handleDownload() {
    downloadReportCsv("pnl", { days });
  }

  return (
    <div>
      <div style={s.toolbar}>
        <PeriodSelector value={days} onChange={setDays} />
        <button style={s.csvBtn} onClick={handleDownload}>⬇ CSV</button>
      </div>

      <div style={s.summaryRow}>
        <div style={s.pill}>
          <span style={s.pillLabel}>Symbols traded</span>
          <span style={s.pillVal}>{summary.symbols_traded ?? 0}</span>
        </div>
        <div style={s.pill}>
          <span style={s.pillLabel}>Total realised P&L</span>
          <span style={s.pillVal}>{fmtCurrency(summary.total_realised_pl)}</span>
        </div>
      </div>

      {isLoading && <p style={s.muted}>Computing P&L…</p>}
      {isError   && <p style={s.err}>Failed to load P&L data.</p>}
      {!isLoading && !isError && rows.length === 0 && (
        <p style={s.muted}>No filled orders found for this period.</p>
      )}

      {rows.length > 0 && (
        <div style={s.tableWrap}>
          <table style={s.table}>
            <thead>
              <tr>
                {["Symbol", "Buy qty", "Buy cost", "Sell qty", "Proceeds", "Realised P&L"].map((h) => (
                  <th key={h} style={s.th}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.symbol} style={s.tr}>
                  <td style={{ ...s.td, fontWeight: 600 }}>{r.symbol}</td>
                  <td style={s.td}>{r.total_buy_qty}</td>
                  <td style={s.td}>${fmt(r.total_bought)}</td>
                  <td style={s.td}>{r.total_sell_qty}</td>
                  <td style={s.td}>${fmt(r.total_sold)}</td>
                  <td style={s.td}>{fmtCurrency(r.realised_pl)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ── Accuracy tab ────────────────────────────────────────────────────────────

function AccuracyTab() {
  const [days, setDays] = useState(30);

  const { data, isLoading, isError } = useQuery({
    queryKey: ["reportAccuracy", days],
    queryFn:  () => getReportAccuracy({ days }),
    staleTime: 60_000,
  });

  const rows = data?.rows ?? [];

  const ACTION_COLORS = { buy: "#48c774", sell: "#f14668", hold: "#667eea" };
  const SOURCE_COLORS = { claude: "#667eea", fallback: "#888" };

  function handleDownload() {
    downloadReportCsv("accuracy", { days });
  }

  return (
    <div>
      <div style={s.toolbar}>
        <PeriodSelector value={days} onChange={setDays} />
        <button style={s.csvBtn} onClick={handleDownload}>⬇ CSV</button>
      </div>

      <p style={{ ...s.muted, marginBottom: 16 }}>
        Shows how often a recommendation was followed by a same-symbol filled order within 48 hours.
      </p>

      {isLoading && <p style={s.muted}>Loading accuracy data…</p>}
      {isError   && <p style={s.err}>Failed to load accuracy data.</p>}
      {!isLoading && !isError && rows.length === 0 && (
        <p style={s.muted}>No recommendation data for this period.</p>
      )}

      {rows.length > 0 && (
        <div style={s.tableWrap}>
          <table style={s.table}>
            <thead>
              <tr>
                {["Source", "Action", "Total recs", "Followed by trade", "Follow-through %"].map((h) => (
                  <th key={h} style={s.th}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((r, i) => (
                <tr key={i} style={s.tr}>
                  <td style={s.td}><Badge text={r.source} colorMap={SOURCE_COLORS} /></td>
                  <td style={s.td}><Badge text={r.action} colorMap={ACTION_COLORS} /></td>
                  <td style={s.td}>{r.total}</td>
                  <td style={s.td}>{r.followed_by_trade}</td>
                  <td style={s.td}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <div style={{ flex: 1, background: "var(--border)", borderRadius: 4, height: 6 }}>
                        <div
                          style={{
                            width: `${Math.min(r.pct_followed, 100)}%`,
                            height: "100%",
                            background: "#667eea",
                            borderRadius: 4,
                          }}
                        />
                      </div>
                      <span style={{ minWidth: 40, textAlign: "right" }}>{r.pct_followed}%</span>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ── Main page ───────────────────────────────────────────────────────────────

const TABS = [
  { id: "trades",   label: "Trade Log" },
  { id: "pnl",      label: "Realised P&L" },
  { id: "accuracy", label: "Rec. Accuracy" },
];

export default function ReportingPage() {
  const [activeTab, setActiveTab] = useState("trades");

  return (
    <div>
      <h2 style={s.pageTitle}>Reports</h2>

      {/* Tab bar */}
      <div style={s.tabBar}>
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => setActiveTab(t.id)}
            style={{ ...s.tab, ...(activeTab === t.id ? s.tabActive : {}) }}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div style={s.tabContent}>
        {activeTab === "trades"   && <TradeLogTab />}
        {activeTab === "pnl"      && <PnlTab />}
        {activeTab === "accuracy" && <AccuracyTab />}
      </div>
    </div>
  );
}

// ── Styles ──────────────────────────────────────────────────────────────────

const s = {
  pageTitle:   { fontSize: 24, fontWeight: 700, marginBottom: 24 },

  tabBar:      { display: "flex", gap: 4, borderBottom: "1px solid var(--border)", marginBottom: 24 },
  tab:         { background: "none", border: "none", padding: "10px 18px", color: "var(--muted)", fontWeight: 500, cursor: "pointer", borderBottom: "2px solid transparent", marginBottom: -1 },
  tabActive:   { color: "var(--accent)", borderBottomColor: "var(--accent)" },

  toolbar:     { display: "flex", gap: 8, alignItems: "center", marginBottom: 16, flexWrap: "wrap" },
  filterInput: { background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 8, color: "var(--fg)", padding: "6px 12px", fontSize: 13 },
  filterSelect:{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 8, color: "var(--fg)", padding: "6px 12px", fontSize: 13 },
  csvBtn:      { background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 8, color: "var(--accent)", padding: "6px 12px", fontWeight: 600, cursor: "pointer", fontSize: 13 },
  periodBtn:   { background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 8, color: "var(--muted)", padding: "5px 12px", cursor: "pointer", fontSize: 12 },
  periodActive:{ background: "rgba(102,126,234,0.15)", borderColor: "var(--accent)", color: "var(--accent)" },

  summaryRow:  { display: "flex", gap: 12, marginBottom: 20, flexWrap: "wrap" },
  pill:        { background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 12, padding: "12px 18px", display: "flex", flexDirection: "column", gap: 4, minWidth: 120 },
  pillLabel:   { fontSize: 11, color: "var(--muted)", textTransform: "uppercase", letterSpacing: 0.5 },
  pillVal:     { fontSize: 20, fontWeight: 700 },

  tableWrap:   { overflowX: "auto" },
  table:       { width: "100%", borderCollapse: "collapse", fontSize: 13 },
  th:          { padding: "10px 12px", textAlign: "left", color: "var(--muted)", fontWeight: 500, borderBottom: "1px solid var(--border)", whiteSpace: "nowrap" },
  tr:          { borderBottom: "1px solid var(--border)" },
  td:          { padding: "10px 12px", verticalAlign: "middle" },

  muted:       { color: "var(--muted)", fontSize: 14 },
  err:         { color: "#f14668", fontSize: 14 },
};
