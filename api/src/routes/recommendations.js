/**
 * GET /api/v1/recommendations — paginated recommendation feed
 * GET /api/v1/recommendations/:symbol — latest for one symbol
 *
 * Task S4-T1-002
 */

import { Router } from "express";
import { z } from "zod";
import { requireAuth } from "../middleware/auth.js";
import { cached } from "../services/redis.js";
import pool from "../services/db.js";

const router = Router();
router.use(requireAuth);

const QuerySchema = z.object({
  symbol:  z.string().optional(),
  source:  z.enum(["claude", "fallback", "all"]).default("all"),
  action:  z.enum(["buy", "sell", "hold", "all"]).default("all"),
  limit:   z.coerce.number().int().min(1).max(100).default(20),
  offset:  z.coerce.number().int().min(0).default(0),
});

/** GET /api/v1/recommendations */
router.get("/", async (req, res, next) => {
  const parse = QuerySchema.safeParse(req.query);
  if (!parse.success) {
    return res.status(400).json({ data: null, error: parse.error.message, meta: {} });
  }

  const { symbol, source, action, limit, offset } = parse.data;
  const cacheKey = `recs:${symbol}:${source}:${action}:${limit}:${offset}`;

  try {
    const data = await cached(cacheKey, 60, async () => {
      const conditions = ["1=1"];
      const params = [];
      let i = 1;

      if (symbol) {
        conditions.push(`s.ticker = $${i++}`);
        params.push(symbol.toUpperCase());
      }
      if (source !== "all") {
        conditions.push(`r.source = $${i++}`);
        params.push(source);
      }
      if (action !== "all") {
        conditions.push(`r.action = $${i++}`);
        params.push(action);
      }

      params.push(limit, offset);
      const rows = await pool.query(
        `SELECT r.id,
                s.ticker,
                r.action,
                r.confidence,
                r.reasoning,
                r.source,
                r.recommended_at,
                r.raw_response->>'key_risks'            AS key_risks,
                r.raw_response->>'suggested_position_size' AS position_size
         FROM   recommendations r
         JOIN   symbols s ON s.id = r.symbol_id
         WHERE  ${conditions.join(" AND ")}
         ORDER  BY r.recommended_at DESC
         LIMIT  $${i++} OFFSET $${i}`,
        params
      );

      const total = await pool.query(
        `SELECT COUNT(*) FROM recommendations r JOIN symbols s ON s.id = r.symbol_id
         WHERE  ${conditions.join(" AND ")}`,
        params.slice(0, -2)
      );

      return { rows: rows.rows, total: parseInt(total.rows[0].count, 10) };
    });

    res.json({
      data: data.rows,
      error: null,
      meta: { total: data.total, limit, offset },
    });
  } catch (err) {
    next(err);
  }
});

/** GET /api/v1/recommendations/:symbol */
router.get("/:symbol", async (req, res, next) => {
  const ticker = req.params.symbol.toUpperCase();
  try {
    const rows = await pool.query(
      `SELECT r.id, s.ticker, r.action, r.confidence, r.reasoning,
              r.source, r.recommended_at, r.raw_response
       FROM   recommendations r
       JOIN   symbols s ON s.id = r.symbol_id
       WHERE  s.ticker = $1
       ORDER  BY r.recommended_at DESC
       LIMIT  1`,
      [ticker]
    );

    if (!rows.rows.length) {
      return res.status(404).json({ data: null, error: `No recommendation found for ${ticker}`, meta: {} });
    }

    res.json({ data: rows.rows[0], error: null, meta: {} });
  } catch (err) {
    next(err);
  }
});

export default router;
