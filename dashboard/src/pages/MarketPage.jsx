import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getMarketData } from "../services/api.js";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";

const SYMBOLS = ["SPY", "QQQ", "GLD", "AAPL", "MSFT", "NVDA"];

function ScoreTile({ ticker, onClick, selected }) {
  const { data, isLoading } = useQuery({
    queryKey: ["market", ticker, 5],
    queryFn: () => getMarketData(ticker, 5),
    staleTime: 300_000,
  });

  const score = data?.scores?.composite_score;
  const change = data?.ohlcv?.length >= 2
    ? ((data.ohlcv.at(-1).close - data.ohlcv.at(-2).close) / data.ohlcv.at(-2).close) * 100
    : null;

  const bg = score == null ? "var(--border)"
    : score >= 65 ? "rgba(72,187,120,0.2)"
    : score <= 35 ? "rgba(252,129,129,0.2)"
    : "rgba(246,224,94,0.1)";

  return (
    <div style={{ ...styles.tile, background: bg, border: `1px solid ${selected ? "var(--accent)" : "var(--border)"}` }}
         onClick={() => onClick(ticker)}>
      <div style={styles.tileTop}>
        <span style={styles.tileTicker}>{ticker}</span>
        {score != null && <span style={styles.tileScore}>{score.toFixed(0)}</span>}
      </div>
      {isLoading ? <span style={styles.muted}>…</span> : (
        <span style={{ color: change >= 0 ? "var(--green)" : "var(--red)", fontSize: 13 }}>
          {change != null ? `${change >= 0 ? "+" : ""}${change.toFixed(2)}%` : "—"}
        </span>
      )}
    </div>
  );
}

export default function MarketPage() {
  const [selected, setSelected] = useState("SPY");

  const { data, isLoading, isError } = useQuery({
    queryKey: ["market", selected, 30],
    queryFn: () => getMarketData(selected, 30),
    staleTime: 300_000,
  });

  const chartData = data?.ohlcv?.map((row) => ({
    date: row.trade_date,
    close: parseFloat(row.close),
  })) ?? [];

  return (
    <div>
      <h2 style={styles.title}>Market Heatmap</h2>
      <div style={styles.heatmap}>
        {SYMBOLS.map((s) => <ScoreTile key={s} ticker={s} onClick={setSelected} selected={s === selected} />)}
      </div>

      <h3 style={{ marginTop: 32, marginBottom: 16, fontSize: 16 }}>{selected} — 30-day Price</h3>

      {isLoading && <p style={styles.muted}>Loading chart…</p>}
      {isError && <p style={styles.error}>Failed to load market data</p>}
      {!isLoading && !isError && (
        <div style={styles.chartWrap}>
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="date" tick={{ fill: "var(--muted)", fontSize: 11 }} tickLine={false} />
              <YAxis domain={["auto","auto"]} tick={{ fill: "var(--muted)", fontSize: 11 }} tickLine={false} axisLine={false} />
              <Tooltip
                contentStyle={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 8 }}
                labelStyle={{ color: "var(--muted)" }}
                itemStyle={{ color: "var(--blue)" }}
              />
              <Line type="monotone" dataKey="close" stroke="var(--blue)" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}

const styles = {
  title:     { fontSize:22, fontWeight:700, marginBottom:20 },
  heatmap:   { display:"grid", gridTemplateColumns:"repeat(auto-fill,minmax(130px,1fr))", gap:12 },
  tile:      { borderRadius:10, padding:14, cursor:"pointer", transition:"transform 0.1s" },
  tileTop:   { display:"flex", justifyContent:"space-between", marginBottom:6 },
  tileTicker:{ fontWeight:700, fontSize:15 },
  tileScore: { fontSize:13, color:"var(--muted)" },
  chartWrap: { background:"var(--surface)", border:"1px solid var(--border)", borderRadius:10, padding:20 },
  muted:     { color:"var(--muted)" },
  error:     { color:"var(--red)" },
};
