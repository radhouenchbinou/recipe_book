import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";
import { getMarketData } from "../services/api.js";

const SYMBOLS = ["SPY", "QQQ", "GLD", "AAPL", "MSFT", "NVDA"];

function ScoreBar({ label, value, max = 100, color = "var(--accent)" }) {
  const pct = Math.max(0, Math.min(100, ((value ?? 0) / max) * 100));
  return (
    <div style={{ marginBottom: 10 }}>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13, marginBottom: 4 }}>
        <span style={{ color: "var(--muted)" }}>{label}</span>
        <span style={{ color: "var(--text)", fontWeight: 600 }}>{value != null ? value.toFixed(1) : "—"}</span>
      </div>
      <div style={{ height: 6, background: "var(--border)", borderRadius: 4 }}>
        <div style={{ width: `${pct}%`, height: "100%", background: color, borderRadius: 4 }} />
      </div>
    </div>
  );
}

function SymbolCard({ symbol }) {
  const { data, isLoading } = useQuery({
    queryKey: ["market-data", symbol, 30],
    queryFn: () => getMarketData(symbol, 30).then ? getMarketData(symbol, 30) : Promise.resolve(null),
  });

  const scores = data?.scores;

  return (
    <div style={styles.card}>
      <div style={styles.cardHeader}>
        <span style={styles.ticker}>{symbol}</span>
        {scores && (
          <span style={{ ...styles.badge, background: scores.composite_score >= 60 ? "#48bb78" : scores.composite_score >= 40 ? "#ed8936" : "#fc8181" }}>
            {scores.composite_score?.toFixed(0) ?? "—"}
          </span>
        )}
      </div>
      {isLoading && <p style={{ color: "var(--muted)", fontSize: 13 }}>Loading…</p>}
      {scores && (
        <>
          <ScoreBar label="Technical" value={scores.technical_score} />
          <ScoreBar label="Sentiment" value={(scores.sentiment_score + 1) * 50} color="#667eea" />
          <ScoreBar label="Geo Risk" value={100 - scores.geo_risk_score} color="#ed8936" />
          <ScoreBar label="Composite" value={scores.composite_score} color="#48bb78" />
        </>
      )}
    </div>
  );
}

export default function AnalysisPage() {
  const queries = SYMBOLS.map((sym) => ({
    symbol: sym,
    query: useQuery({
      queryKey: ["market-data", sym, 30],
      queryFn: () => getMarketData(sym, 30),
      staleTime: 300_000,
    }),
  }));

  const chartData = queries
    .filter(({ query }) => query.data?.scores)
    .map(({ symbol, query }) => ({
      symbol,
      composite: query.data.scores.composite_score ?? 0,
    }));

  return (
    <div>
      <h1 style={styles.heading}>Analysis Scorecards</h1>

      {chartData.length > 0 && (
        <div style={styles.chartWrap}>
          <h2 style={styles.subheading}>Composite Score by Symbol</h2>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={chartData} margin={{ left: -20 }}>
              <XAxis dataKey="symbol" tick={{ fill: "var(--muted)", fontSize: 12 }} />
              <YAxis domain={[0, 100]} tick={{ fill: "var(--muted)", fontSize: 12 }} />
              <Tooltip
                contentStyle={{ background: "var(--surface)", border: "1px solid var(--border)" }}
                labelStyle={{ color: "var(--text)" }}
              />
              <Bar dataKey="composite" radius={[4, 4, 0, 0]}>
                {chartData.map(({ composite }, i) => (
                  <Cell key={i} fill={composite >= 60 ? "#48bb78" : composite >= 40 ? "#ed8936" : "#fc8181"} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      <div style={styles.grid}>
        {SYMBOLS.map((sym) => <SymbolCard key={sym} symbol={sym} />)}
      </div>
    </div>
  );
}

const styles = {
  heading:    { fontSize: 24, fontWeight: 700, marginBottom: 8 },
  subheading: { fontSize: 16, fontWeight: 600, color: "var(--muted)", marginBottom: 12 },
  chartWrap:  { background: "var(--surface)", borderRadius: 12, padding: 24, marginBottom: 24 },
  grid:       { display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 16 },
  card:       { background: "var(--surface)", borderRadius: 12, padding: 20 },
  cardHeader: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 },
  ticker:     { fontSize: 18, fontWeight: 700 },
  badge:      { borderRadius: 20, padding: "2px 10px", fontSize: 13, fontWeight: 700, color: "#fff" },
};
