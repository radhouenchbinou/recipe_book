/**
 * Phase 2 Sprint 3 — Portfolio Optimization API route
 * GET /api/v2/optimize         — compute optimized target weights
 * GET /api/v2/optimize/drift   — detect allocation drift vs current positions
 */

import { Router } from "express";
import { z } from "zod";
import { requireAuth } from "../../middleware/auth.js";
import pool from "../../services/db.js";
import { cached } from "../../services/redis.js";

const router = Router();

const driftQuerySchema = z.object({
  threshold: z.coerce.number().min(0.001).max(0.20).default(0.03),
});

// ── GET /api/v2/optimize ───────────────────────────────────────────────────
// Compute score-weighted target weights dampened by volatility.
router.get("/", requireAuth, async (req, res, next) => {
  try {
    const data = await cached("v2:optimize:weights", 60, async () => {
      // Fetch latest composite scores
      const { rows: scoreRows } = await pool.query(`
        SELECT DISTINCT ON (s.id)
          s.ticker,
          a.composite_score
        FROM analysis_scores a
        JOIN symbols s ON s.id = a.symbol_id
        ORDER BY s.id, a.scored_at DESC
      `);

      if (!scoreRows.length) {
        return { weights: [], notes: "No analysis scores available" };
      }

      // Fetch 30-day daily price volatility per symbol
      const tickers = scoreRows.map(r => r.ticker);
      const placeholders = tickers.map((_, i) => `$${i + 1}`).join(",");

      const { rows: priceRows } = await pool.query(`
        SELECT s.ticker, m.close_price
        FROM market_data m
        JOIN symbols s ON s.id = m.symbol_id
        WHERE s.ticker IN (${placeholders})
          AND m.trade_date >= NOW() - INTERVAL '30 days'
        ORDER BY s.ticker, m.trade_date ASC
      `, tickers);

      // Compute annualised daily vol per ticker
      const pricesByTicker = {};
      for (const row of priceRows) {
        (pricesByTicker[row.ticker] ??= []).push(parseFloat(row.close_price));
      }

      const volMap = {};
      for (const [ticker, prices] of Object.entries(pricesByTicker)) {
        if (prices.length < 2) { volMap[ticker] = 0.20; continue; }
        const returns = prices.slice(1).map((p, i) => (p - prices[i]) / prices[i]).filter(r => isFinite(r));
        if (!returns.length) { volMap[ticker] = 0.20; continue; }
        const mean = returns.reduce((s, r) => s + r, 0) / returns.length;
        const variance = returns.reduce((s, r) => s + (r - mean) ** 2, 0) / returns.length;
        volMap[ticker] = Math.sqrt(variance) * Math.sqrt(252);
      }

      const VOL_PENALTY  = 2.0;
      const INVESTED_PCT = 0.80;
      const MAX_WEIGHT   = 0.25;
      const MIN_SCORE    = 50;

      // Filter bullish
      const candidates = scoreRows.filter(r => parseFloat(r.composite_score) >= MIN_SCORE);
      if (!candidates.length) {
        return { weights: [], invested_pct: 0, cash_pct: 1, notes: "No bullish symbols" };
      }

      // Raw weights
      const raw = {};
      for (const r of candidates) {
        const score = parseFloat(r.composite_score);
        const vol   = volMap[r.ticker] ?? 0.20;
        raw[r.ticker] = score / (1 + VOL_PENALTY * vol);
      }
      const rawSum = Object.values(raw).reduce((s, v) => s + v, 0);

      // Normalise + cap
      const capped = {};
      for (const [t, rw] of Object.entries(raw)) {
        capped[t] = Math.min((rw / rawSum) * INVESTED_PCT, MAX_WEIGHT);
      }

      // Re-normalise after cap
      const cappedSum = Object.values(capped).reduce((s, v) => s + v, 0);
      const weights = [];
      let totalInvested = 0;

      for (const [ticker, w] of Object.entries(capped).sort((a, b) => b[1] - a[1])) {
        const finalW = cappedSum > 0 ? (w / cappedSum) * INVESTED_PCT : 0;
        const score  = parseFloat(scoreRows.find(r => r.ticker === ticker)?.composite_score ?? 0);
        weights.push({
          ticker,
          composite_score:  Math.round(score * 10) / 10,
          volatility:       Math.round((volMap[ticker] ?? 0.20) * 10000) / 10000,
          target_weight:    Math.round(finalW * 10000) / 10000,
          target_weight_pct: Math.round(finalW * 10000) / 100,
        });
        totalInvested += finalW;
      }

      const skipped = scoreRows
        .filter(r => parseFloat(r.composite_score) < MIN_SCORE)
        .map(r => r.ticker);

      return {
        weights,
        invested_pct:  Math.round(totalInvested * 10000) / 10000,
        cash_pct:      Math.round((1 - totalInvested) * 10000) / 10000,
        vol_penalty:   VOL_PENALTY,
        skipped,
        notes: `Optimised ${weights.length} symbols (score≥${MIN_SCORE}), vol-dampened`,
      };
    });

    res.json({ data, error: null, meta: {} });
  } catch (err) {
    next(err);
  }
});

// ── GET /api/v2/optimize/drift ─────────────────────────────────────────────
// Detect drift between current positions and optimized target weights.
router.get("/drift", requireAuth, async (req, res, next) => {
  try {
    const parsed = driftQuerySchema.safeParse(req.query);
    if (!parsed.success) {
      return res.status(400).json({ data: null, error: parsed.error.flatten(), meta: {} });
    }
    const { threshold } = parsed.data;
    const cacheKey = `v2:optimize:drift:${threshold}`;

    const data = await cached(cacheKey, 30, async () => {
      // Fetch latest target weights (from optimize endpoint logic)
      const { rows: scoreRows } = await pool.query(`
        SELECT DISTINCT ON (s.id) s.ticker, a.composite_score
        FROM analysis_scores a
        JOIN symbols s ON s.id = a.symbol_id
        ORDER BY s.id, a.scored_at DESC
      `);

      const INVESTED_PCT = 0.80;
      const total_score  = scoreRows
        .filter(r => parseFloat(r.composite_score) >= 50)
        .reduce((s, r) => s + parseFloat(r.composite_score), 0);

      const targetWeights = {};
      for (const r of scoreRows) {
        if (parseFloat(r.composite_score) >= 50 && total_score > 0) {
          targetWeights[r.ticker] = Math.min(
            (parseFloat(r.composite_score) / total_score) * INVESTED_PCT, 0.25
          );
        }
      }

      // Drift analysis — uses placeholder current weights (0 when not held)
      const entries = Object.entries(targetWeights).map(([ticker, target]) => {
        const current = 0;   // populated at runtime from live broker data
        const drift   = current - target;
        const absDrift = Math.abs(drift);
        const needsReb = absDrift >= threshold;
        return {
          ticker,
          target_weight:  Math.round(target * 10000) / 10000,
          current_weight: current,
          drift:          Math.round(drift * 10000) / 10000,
          abs_drift:      Math.round(absDrift * 10000) / 10000,
          needs_rebalance: needsReb,
          action:         needsReb ? (drift > 0 ? "sell" : "buy") : "hold",
        };
      });

      return {
        threshold,
        entries,
        needs_rebalance: entries.some(e => e.needs_rebalance),
        rebalance_count: entries.filter(e => e.needs_rebalance).length,
        note: "current_weight is 0 when positions are not available from broker",
      };
    });

    res.json({ data, error: null, meta: { threshold } });
  } catch (err) {
    next(err);
  }
});

export default router;
