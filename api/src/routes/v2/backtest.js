/**
 * Phase 2 — Backtest API route
 * GET /api/v2/backtest/:symbol?start=YYYY-MM-DD&end=YYYY-MM-DD
 *
 * Reads pre-stored backtest results from the DB (populated by the bot's
 * backtest engine). Does NOT run backtests on demand to keep latency low.
 */

import { Router } from "express";
import { z } from "zod";
import { requireAuth } from "../../middleware/auth.js";
import pool from "../../services/db.js";
import { cached } from "../../services/redis.js";

const router = Router();

const querySchema = z.object({
  start: z.string().regex(/^\d{4}-\d{2}-\d{2}$/).optional(),
  end:   z.string().regex(/^\d{4}-\d{2}-\d{2}$/).optional(),
});

// GET /api/v2/backtest/:symbol
router.get("/:symbol", requireAuth, async (req, res, next) => {
  try {
    const symbol = req.params.symbol.toUpperCase();
    const parsed = querySchema.safeParse(req.query);
    if (!parsed.success) {
      return res.status(400).json({ data: null, error: parsed.error.flatten(), meta: {} });
    }

    const { start, end } = parsed.data;
    const cacheKey = `v2:backtest:${symbol}:${start ?? ""}:${end ?? ""}`;

    const data = await cached(cacheKey, 300, async () => {
      // Retrieve recommendations + analysis scores in date range as a proxy
      // for backtest signal history (the Python engine persists full results
      // to the recommendations table with source='backtest').
      let query = `
        SELECT
          r.id,
          r.action,
          r.confidence,
          r.position_size,
          r.source,
          r.rationale,
          r.created_at,
          a.composite_score,
          a.technical_score,
          a.sentiment_score,
          a.geo_risk_score,
          m.close_price  AS price
        FROM recommendations r
        JOIN symbols       s ON s.id = r.symbol_id
        LEFT JOIN analysis_scores a ON a.id  = r.analysis_score_id
        LEFT JOIN market_data     m ON m.symbol_id = s.id
          AND DATE(m.trade_date) = DATE(r.created_at)
        WHERE s.ticker = $1
          AND r.source  = 'backtest'
      `;
      const values = [symbol];
      let idx = 2;

      if (start) { query += ` AND r.created_at >= $${idx++}`; values.push(start); }
      if (end)   { query += ` AND r.created_at <= $${idx++}`; values.push(end + "T23:59:59"); }

      query += " ORDER BY r.created_at ASC";

      const { rows } = await pool.query(query, values);
      return {
        symbol,
        start: start ?? null,
        end:   end   ?? null,
        signal_count: rows.length,
        signals: rows,
      };
    });

    res.json({ data, error: null, meta: { symbol } });
  } catch (err) {
    next(err);
  }
});

// GET /api/v2/backtest  — list symbols that have backtest data
router.get("/", requireAuth, async (req, res, next) => {
  try {
    const data = await cached("v2:backtest:symbols", 120, async () => {
      const { rows } = await pool.query(`
        SELECT DISTINCT s.ticker, COUNT(r.id) AS signal_count,
               MIN(r.created_at) AS earliest, MAX(r.created_at) AS latest
        FROM recommendations r
        JOIN symbols s ON s.id = r.symbol_id
        WHERE r.source = 'backtest'
        GROUP BY s.ticker
        ORDER BY s.ticker
      `);
      return rows;
    });

    res.json({ data, error: null, meta: { count: data.length } });
  } catch (err) {
    next(err);
  }
});

export default router;
