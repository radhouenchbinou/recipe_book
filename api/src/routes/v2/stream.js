/**
 * Phase 3 Sprint 1 — Real-time price streaming via Server-Sent Events (SSE)
 *
 * GET /api/v2/stream/prices?symbols=AAPL,SPY,GLD
 *
 * Uses SSE (text/event-stream) instead of WebSockets to avoid needing
 * a separate WS server — works transparently through the nginx proxy.
 *
 * The stream polls the DB every 5 seconds and pushes the latest close
 * prices for the requested symbols.  The client reconnects automatically
 * (EventSource spec) if the connection drops.
 *
 * Auth: Bearer token in query param `token` (SSE can't set headers).
 */

import { Router } from "express";
import jwt from "jsonwebtoken";
import pool from "../../services/db.js";

const router = Router();
const POLL_INTERVAL_MS = 5_000;
const MAX_SYMBOLS = 10;

// ── GET /api/v2/stream/prices ─────────────────────────────────────────────
router.get("/prices", async (req, res) => {
  // Auth via query param (SSE limitation — browsers can't set headers)
  const token = req.query.token;
  if (!token) {
    return res.status(401).json({ data: null, error: "Missing token", meta: {} });
  }
  try {
    jwt.verify(token, process.env.JWT_SECRET ?? "dev-secret");
  } catch {
    return res.status(401).json({ data: null, error: "Invalid token", meta: {} });
  }

  // Parse requested symbols
  const rawSymbols = String(req.query.symbols ?? "").split(",").map(s => s.trim().toUpperCase()).filter(Boolean);
  const symbols = rawSymbols.slice(0, MAX_SYMBOLS);

  if (!symbols.length) {
    return res.status(400).json({ data: null, error: "No symbols provided", meta: {} });
  }

  // ── Set up SSE response ─────────────────────────────────────────────────
  res.setHeader("Content-Type", "text/event-stream");
  res.setHeader("Cache-Control", "no-cache");
  res.setHeader("Connection", "keep-alive");
  res.setHeader("X-Accel-Buffering", "no");   // disable nginx buffering
  res.flushHeaders();

  const send = (event, data) => {
    try {
      res.write(`event: ${event}\ndata: ${JSON.stringify(data)}\n\n`);
    } catch {
      // client disconnected
    }
  };

  // Send initial connection confirmation
  send("connected", { symbols, poll_interval_ms: POLL_INTERVAL_MS });

  // ── Poll loop ───────────────────────────────────────────────────────────
  async function fetchAndSend() {
    try {
      const placeholders = symbols.map((_, i) => `$${i + 1}`).join(",");
      const { rows } = await pool.query(`
        SELECT DISTINCT ON (s.id)
          s.ticker,
          m.close_price,
          m.trade_date,
          a.composite_score
        FROM market_data m
        JOIN symbols s ON s.id = m.symbol_id
        LEFT JOIN LATERAL (
          SELECT a2.composite_score
          FROM analysis_scores a2
          WHERE a2.symbol_id = s.id
          ORDER BY a2.scored_at DESC LIMIT 1
        ) a ON TRUE
        WHERE s.ticker IN (${placeholders})
        ORDER BY s.id, m.trade_date DESC
      `, symbols);

      const payload = rows.map(r => ({
        ticker:          r.ticker,
        close_price:     parseFloat(r.close_price),
        trade_date:      r.trade_date,
        composite_score: r.composite_score ? parseFloat(r.composite_score) : null,
      }));

      send("prices", { ts: Date.now(), data: payload });
    } catch (err) {
      send("error", { message: err.message });
    }
  }

  // Immediate first push, then poll
  await fetchAndSend();
  const interval = setInterval(fetchAndSend, POLL_INTERVAL_MS);

  // Clean up on disconnect
  req.on("close", () => {
    clearInterval(interval);
  });
});

export default router;
