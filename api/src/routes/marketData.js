/**
 * GET /api/v1/market-data/:symbol — OHLCV + latest indicators
 *
 * Task S4-T1-003
 */

import { Router } from "express";
import { z } from "zod";
import { requireAuth } from "../middleware/auth.js";
import { cached } from "../services/redis.js";
import pool from "../services/db.js";

const router = Router();
router.use(requireAuth);

const QuerySchema = z.object({
  days: z.coerce.number().int().min(1).max(365).default(30),
});

/** GET /api/v1/market-data/:symbol */
router.get("/:symbol", async (req, res, next) => {
  const ticker = req.params.symbol.toUpperCase();
  const parse = QuerySchema.safeParse(req.query);
  if (!parse.success) {
    return res.status(400).json({ data: null, error: parse.error.message, meta: {} });
  }

  const { days } = parse.data;
  const cacheKey = `market:${ticker}:${days}`;

  try {
    const data = await cached(cacheKey, 300, async () => {
      // OHLCV history
      const ohlcv = await pool.query(
        `SELECT md.trade_date, md.open, md.high, md.low, md.close, md.volume
         FROM   market_data md
         JOIN   symbols s ON s.id = md.symbol_id
         WHERE  s.ticker = $1
           AND  md.trade_date >= CURRENT_DATE - $2 * INTERVAL '1 day'
         ORDER  BY md.trade_date ASC`,
        [ticker, days]
      );

      // Latest analysis scores / indicators
      const scores = await pool.query(
        `SELECT a.technical_score, a.sentiment_score, a.geo_risk_score,
                a.composite_score, a.indicator_snapshot, a.scored_at
         FROM   analysis_scores a
         JOIN   symbols s ON s.id = a.symbol_id
         WHERE  s.ticker = $1
         ORDER  BY a.scored_at DESC
         LIMIT  1`,
        [ticker]
      );

      return {
        ticker,
        ohlcv: ohlcv.rows,
        scores: scores.rows[0] ?? null,
      };
    });

    if (!data.ohlcv.length) {
      return res.status(404).json({ data: null, error: `No market data found for ${ticker}`, meta: {} });
    }

    res.json({ data, error: null, meta: { days, cached_ttl: 300 } });
  } catch (err) {
    next(err);
  }
});

export default router;
