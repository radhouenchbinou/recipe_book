/**
 * Phase 3 Sprint 2 — Trade & Performance Report API
 * GET /api/v2/report/trades        — paginated order ledger
 * GET /api/v2/report/pnl           — realised P&L by symbol
 * GET /api/v2/report/accuracy      — recommendation follow-through stats
 *
 * All endpoints support ?format=json (default) or ?format=csv
 * CSV responses set Content-Disposition: attachment for direct download.
 */

import { Router } from "express";
import { z } from "zod";
import { requireAuth } from "../../middleware/auth.js";
import pool from "../../services/db.js";

const router = Router();

// ── Shared query schemas ────────────────────────────────────────────────────

const baseSchema = z.object({
  days:   z.coerce.number().int().min(1).max(365).default(30),
  format: z.enum(["json", "csv"]).default("json"),
});

const tradesSchema = baseSchema.extend({
  symbol: z.string().max(10).optional(),
  broker: z.string().max(50).optional(),
  status: z.string().max(20).optional(),
  limit:  z.coerce.number().int().min(1).max(1000).default(200),
});

const pnlSchema = baseSchema.extend({
  symbol: z.string().max(10).optional(),
  days:   z.coerce.number().int().min(1).max(365).default(90),
});

// ── Helper: CSV response ────────────────────────────────────────────────────

function sendCsv(res, filename, rows) {
  if (rows.length === 0) {
    res.setHeader("Content-Type", "text/csv");
    res.setHeader("Content-Disposition", `attachment; filename="${filename}"`);
    return res.send("");
  }
  const headers = Object.keys(rows[0]).join(",");
  const lines   = rows.map((r) =>
    Object.values(r)
      .map((v) => (v === null || v === undefined ? "" : String(v).replace(/,/g, ";")))
      .join(",")
  );
  res.setHeader("Content-Type", "text/csv");
  res.setHeader("Content-Disposition", `attachment; filename="${filename}"`);
  res.send([headers, ...lines].join("\n"));
}

// ── GET /api/v2/report/trades ─────────────────────────────────────────────

router.get("/trades", requireAuth, async (req, res, next) => {
  try {
    const q = tradesSchema.parse(req.query);

    const conditions = ["o.created_at >= NOW() - $1::interval"];
    const params     = [`${q.days} days`];
    let   idx        = 2;

    if (q.symbol) { conditions.push(`o.symbol = $${idx++}`); params.push(q.symbol); }
    if (q.broker) { conditions.push(`o.broker = $${idx++}`); params.push(q.broker); }
    if (q.status) { conditions.push(`o.status = $${idx++}`); params.push(q.status); }

    params.push(q.limit);
    const where = conditions.join(" AND ");

    const { rows } = await pool.query(
      `SELECT o.id, o.order_id, o.broker, o.symbol, o.side,
              o.qty, o.status,
              CAST(o.filled_price AS FLOAT) AS filled_price,
              o.error, o.source, o.created_at
       FROM order_ledger o
       WHERE ${where}
       ORDER BY o.created_at DESC
       LIMIT $${idx}`,
      params
    );

    const summary = {
      total_orders:  rows.length,
      filled_buys:   rows.filter((r) => r.side === "buy"  && r.status === "filled").length,
      filled_sells:  rows.filter((r) => r.side === "sell" && r.status === "filled").length,
      rejected:      rows.filter((r) => r.status === "rejected").length,
    };

    if (q.format === "csv") return sendCsv(res, "trades.csv", rows);

    res.json({
      data:  { summary, rows },
      error: null,
      meta:  { filters: q, generated_at: new Date().toISOString() },
    });
  } catch (err) {
    if (err.name === "ZodError") {
      return res.status(400).json({ data: null, error: err.errors, meta: {} });
    }
    next(err);
  }
});

// ── GET /api/v2/report/pnl ────────────────────────────────────────────────

router.get("/pnl", requireAuth, async (req, res, next) => {
  try {
    const q = pnlSchema.parse(req.query);

    const conditions = ["o.status = 'filled'", "o.created_at >= NOW() - $1::interval"];
    const params     = [`${q.days} days`];
    let   idx        = 2;

    if (q.symbol) { conditions.push(`o.symbol = $${idx++}`); params.push(q.symbol); }

    const { rows: raw } = await pool.query(
      `SELECT o.symbol, o.side, o.qty, CAST(o.filled_price AS FLOAT) AS filled_price
       FROM order_ledger o
       WHERE ${conditions.join(" AND ")}
       ORDER BY o.symbol, o.created_at`,
      params
    );

    // Group by symbol, compute buy cost and sell proceeds
    const bySymbol = {};
    for (const r of raw) {
      if (!bySymbol[r.symbol]) {
        bySymbol[r.symbol] = { buys: [], sells: [] };
      }
      bySymbol[r.symbol][r.side === "buy" ? "buys" : "sells"].push(
        { qty: Number(r.qty), price: r.filled_price ?? 0 }
      );
    }

    const pnlRows = Object.entries(bySymbol).map(([symbol, data]) => {
      const totalBought  = data.buys.reduce((s, o)  => s + o.qty * o.price, 0);
      const totalSold    = data.sells.reduce((s, o) => s + o.qty * o.price, 0);
      const realisedPl   = totalSold - totalBought;
      return {
        symbol,
        total_bought:   Number(totalBought.toFixed(2)),
        total_sold:     Number(totalSold.toFixed(2)),
        realised_pl:    Number(realisedPl.toFixed(2)),
        total_buy_qty:  data.buys.reduce((s, o) => s + o.qty, 0),
        total_sell_qty: data.sells.reduce((s, o) => s + o.qty, 0),
      };
    });

    pnlRows.sort((a, b) => b.realised_pl - a.realised_pl);
    const totalPl = pnlRows.reduce((s, r) => s + r.realised_pl, 0);

    if (q.format === "csv") return sendCsv(res, "pnl.csv", pnlRows);

    res.json({
      data: {
        summary: { symbols_traded: pnlRows.length, total_realised_pl: Number(totalPl.toFixed(2)) },
        rows:    pnlRows,
      },
      error: null,
      meta:  { filters: q, generated_at: new Date().toISOString() },
    });
  } catch (err) {
    if (err.name === "ZodError") {
      return res.status(400).json({ data: null, error: err.errors, meta: {} });
    }
    next(err);
  }
});

// ── GET /api/v2/report/accuracy ───────────────────────────────────────────

router.get("/accuracy", requireAuth, async (req, res, next) => {
  try {
    const q = baseSchema.parse(req.query);

    const { rows } = await pool.query(
      `SELECT r.source, r.action,
              COUNT(*)::int AS total,
              COUNT(o.id)::int AS followed_by_trade
       FROM recommendations r
       JOIN symbols s ON s.id = r.symbol_id
       LEFT JOIN order_ledger o
              ON o.symbol  = s.ticker
             AND o.created_at BETWEEN r.created_at AND r.created_at + INTERVAL '2 days'
             AND o.status  = 'filled'
       WHERE r.created_at >= NOW() - $1::interval
       GROUP BY r.source, r.action
       ORDER BY r.source, r.action`,
      [`${q.days} days`]
    );

    const accRows = rows.map((r) => ({
      source:             r.source,
      action:             r.action,
      total:              r.total,
      followed_by_trade:  r.followed_by_trade,
      pct_followed:       r.total > 0 ? Number((r.followed_by_trade / r.total * 100).toFixed(1)) : 0,
    }));

    if (q.format === "csv") return sendCsv(res, "accuracy.csv", accRows);

    res.json({
      data:  { groups: accRows.length, rows: accRows },
      error: null,
      meta:  { filters: q, generated_at: new Date().toISOString() },
    });
  } catch (err) {
    if (err.name === "ZodError") {
      return res.status(400).json({ data: null, error: err.errors, meta: {} });
    }
    next(err);
  }
});

export default router;
