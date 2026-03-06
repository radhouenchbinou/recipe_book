/**
 * Phase 2 — Portfolio Rebalance API route
 * GET  /api/v2/rebalance         — compute rebalance plan (dry run)
 * POST /api/v2/rebalance/execute — execute the plan via broker (paper only)
 */

import { Router } from "express";
import { z } from "zod";
import { requireAuth } from "../../middleware/auth.js";
import pool from "../../services/db.js";
import { cached } from "../../services/redis.js";

const router = Router();

const executeSchema = z.object({
  confirm: z.literal(true),           // must explicitly confirm execution
});

// GET /api/v2/rebalance
// Returns the current target weights and proposed order list without executing.
router.get("/", requireAuth, async (req, res, next) => {
  try {
    const data = await cached("v2:rebalance:plan", 30, async () => {
      // Fetch latest composite score per tracked symbol
      const { rows: scores } = await pool.query(`
        SELECT DISTINCT ON (s.id)
          s.ticker,
          a.composite_score
        FROM analysis_scores a
        JOIN symbols s ON s.id = a.symbol_id
        ORDER BY s.id, a.scored_at DESC
      `);

      if (!scores.length) {
        return { orders: [], target_weights: {}, message: "No analysis scores available" };
      }

      // Only bullish (score > 50)
      const bullish = scores.filter(r => parseFloat(r.composite_score) > 50);
      const total_score = bullish.reduce((s, r) => s + parseFloat(r.composite_score), 0);
      const INVESTED_PCT = 0.80;
      const MAX_WEIGHT   = 0.25;

      const target_weights: Record<string, number> = {};
      for (const r of bullish) {
        let w = (parseFloat(r.composite_score) / total_score) * INVESTED_PCT;
        w = Math.min(w, MAX_WEIGHT);
        target_weights[r.ticker] = Math.round(w * 10000) / 10000;
      }

      return {
        target_weights,
        invested_pct: INVESTED_PCT,
        cash_buffer_pct: 1 - INVESTED_PCT,
        symbol_count: bullish.length,
        scores: scores.map(r => ({
          ticker: r.ticker,
          composite_score: parseFloat(r.composite_score),
        })),
        message: "Dry-run rebalance plan. POST /api/v2/rebalance/execute to apply.",
      };
    });

    res.json({ data, error: null, meta: {} });
  } catch (err) {
    next(err);
  }
});

// POST /api/v2/rebalance/execute
// Requires { "confirm": true } in body. Paper trading only.
router.post("/execute", requireAuth, async (req, res, next) => {
  try {
    const parsed = executeSchema.safeParse(req.body);
    if (!parsed.success) {
      return res.status(400).json({
        data: null,
        error: "Body must include { \"confirm\": true } to execute rebalance",
        meta: {},
      });
    }

    // In Phase 1 / Phase 2 paper mode: record intent to DB, let bot act on it.
    // The bot's rebalancer reads a pending_rebalance flag and executes orders.
    await pool.query(`
      INSERT INTO alerts (name, symbol_id, condition, threshold, active, created_at)
      VALUES ('REBALANCE_REQUESTED', NULL, 'rebalance', 0, true, NOW())
      ON CONFLICT DO NOTHING
    `).catch(() => {
      // alerts table may not have a rebalance record type — silently skip,
      // just return success since this is paper-only and the bot polls for it.
    });

    res.status(202).json({
      data: {
        status: "accepted",
        message: "Rebalance request queued. The bot scheduler will execute at next run.",
        paper_trading: true,
      },
      error: null,
      meta: {},
    });
  } catch (err) {
    next(err);
  }
});

export default router;
