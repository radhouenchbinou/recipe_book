/**
 * Phase 2 — Performance Analytics API route
 * GET /api/v2/performance           — portfolio-level aggregate
 * GET /api/v2/performance/:symbol   — per-symbol stats
 */

import { Router } from "express";
import { requireAuth } from "../../middleware/auth.js";
import pool from "../../services/db.js";
import { cached } from "../../services/redis.js";

const router = Router();

// GET /api/v2/performance
router.get("/", requireAuth, async (req, res, next) => {
  try {
    const data = await cached("v2:performance:portfolio", 60, async () => {
      const [recStats, symbolStats, usageStats] = await Promise.all([
        // Recommendation breakdown
        pool.query(`
          SELECT
            COUNT(*)                                          AS total,
            SUM(CASE WHEN action='buy'      THEN 1 ELSE 0 END) AS buy_count,
            SUM(CASE WHEN action='sell'     THEN 1 ELSE 0 END) AS sell_count,
            SUM(CASE WHEN action='hold'     THEN 1 ELSE 0 END) AS hold_count,
            SUM(CASE WHEN source='claude'   THEN 1 ELSE 0 END) AS claude_count,
            SUM(CASE WHEN source='fallback' THEN 1 ELSE 0 END) AS fallback_count,
            ROUND(AVG(confidence)::numeric, 4)               AS avg_confidence
          FROM recommendations
        `),

        // Per-symbol aggregate
        pool.query(`
          SELECT
            s.ticker,
            COUNT(r.id)                                            AS rec_count,
            SUM(CASE WHEN r.action='buy'      THEN 1 ELSE 0 END)  AS buy_count,
            SUM(CASE WHEN r.action='sell'     THEN 1 ELSE 0 END)  AS sell_count,
            SUM(CASE WHEN r.action='hold'     THEN 1 ELSE 0 END)  AS hold_count,
            ROUND(AVG(r.confidence)::numeric, 4)                  AS avg_confidence,
            ROUND(AVG(a.composite_score)::numeric, 2)             AS avg_composite
          FROM recommendations r
          JOIN symbols s ON s.id = r.symbol_id
          LEFT JOIN analysis_scores a ON a.id = r.analysis_score_id
          GROUP BY s.ticker
          ORDER BY rec_count DESC
        `),

        // Claude usage today
        pool.query(`
          SELECT
            COALESCE(SUM(input_tokens + output_tokens), 0) AS tokens_today,
            COUNT(*)                                        AS calls_today
          FROM claude_usage
          WHERE DATE(called_at) = CURRENT_DATE
        `),
      ]);

      const agg = recStats.rows[0];
      return {
        recommendations: {
          total:          parseInt(agg.total          || 0),
          buy_count:      parseInt(agg.buy_count      || 0),
          sell_count:     parseInt(agg.sell_count     || 0),
          hold_count:     parseInt(agg.hold_count     || 0),
          claude_count:   parseInt(agg.claude_count   || 0),
          fallback_count: parseInt(agg.fallback_count || 0),
          avg_confidence: parseFloat(agg.avg_confidence || 0),
        },
        symbols: symbolStats.rows.map(r => ({
          ticker:         r.ticker,
          rec_count:      parseInt(r.rec_count      || 0),
          buy_count:      parseInt(r.buy_count      || 0),
          sell_count:     parseInt(r.sell_count     || 0),
          hold_count:     parseInt(r.hold_count     || 0),
          avg_confidence: parseFloat(r.avg_confidence || 0),
          avg_composite:  parseFloat(r.avg_composite  || 0),
        })),
        claude_usage_today: {
          tokens: parseInt(usageStats.rows[0]?.tokens_today || 0),
          calls:  parseInt(usageStats.rows[0]?.calls_today  || 0),
        },
      };
    });

    res.json({ data, error: null, meta: {} });
  } catch (err) {
    next(err);
  }
});

// GET /api/v2/performance/:symbol
router.get("/:symbol", requireAuth, async (req, res, next) => {
  try {
    const symbol = req.params.symbol.toUpperCase();
    const cacheKey = `v2:performance:${symbol}`;

    const data = await cached(cacheKey, 60, async () => {
      const { rows } = await pool.query(`
        SELECT
          r.id,
          r.action,
          r.confidence,
          r.position_size,
          r.source,
          r.created_at,
          a.composite_score,
          a.technical_score,
          a.sentiment_score,
          a.geo_risk_score
        FROM recommendations r
        JOIN symbols s ON s.id = r.symbol_id
        LEFT JOIN analysis_scores a ON a.id = r.analysis_score_id
        WHERE s.ticker = $1
        ORDER BY r.created_at DESC
        LIMIT 100
      `, [symbol]);

      if (!rows.length) {
        return { symbol, history: [], summary: null };
      }

      const total = rows.length;
      const buys  = rows.filter(r => r.action === "buy").length;
      const sells = rows.filter(r => r.action === "sell").length;
      const avgConf = rows.reduce((s, r) => s + parseFloat(r.confidence || 0), 0) / total;
      const avgComp = rows.reduce((s, r) => s + parseFloat(r.composite_score || 0), 0) / total;

      return {
        symbol,
        summary: {
          total,
          buy_count:      buys,
          sell_count:     sells,
          hold_count:     total - buys - sells,
          avg_confidence: Math.round(avgConf * 10000) / 10000,
          avg_composite:  Math.round(avgComp * 100) / 100,
        },
        history: rows,
      };
    });

    res.json({ data, error: null, meta: { symbol } });
  } catch (err) {
    next(err);
  }
});

export default router;
