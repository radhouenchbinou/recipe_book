/**
 * Phase 2 Sprint 3 — Advanced Risk Metrics API route
 * GET /api/v2/risk                     — portfolio-level VaR, CVaR, beta, correlation
 * GET /api/v2/risk/:symbol             — single-symbol risk metrics
 */

import { Router } from "express";
import { z } from "zod";
import { requireAuth } from "../../middleware/auth.js";
import pool from "../../services/db.js";
import { cached } from "../../services/redis.js";

const router = Router();

const querySchema = z.object({
  days:       z.coerce.number().int().min(30).max(504).default(252),
  confidence: z.coerce.number().min(0.90).max(0.99).default(0.95),
  benchmark:  z.string().default("SPY"),
});

/** Compute daily returns array from an array of prices. */
function dailyReturns(prices) {
  const rets = [];
  for (let i = 1; i < prices.length; i++) {
    if (prices[i - 1] > 0) rets.push((prices[i] - prices[i - 1]) / prices[i - 1]);
  }
  return rets;
}

/** Historical VaR at given confidence level. Returns negative number (loss %). */
function historicalVar(returns, confidence) {
  if (!returns.length) return null;
  const sorted = [...returns].sort((a, b) => a - b);
  const idx    = Math.max(0, Math.floor(sorted.length * (1 - confidence)) - 1);
  return sorted[idx] * 100;
}

/** CVaR — average of returns below VaR cutoff. */
function historicalCVar(returns, confidence) {
  if (!returns.length) return null;
  const sorted  = [...returns].sort((a, b) => a - b);
  const cutoff  = Math.max(1, Math.floor(sorted.length * (1 - confidence)));
  const tail    = sorted.slice(0, cutoff);
  return tail.reduce((s, r) => s + r, 0) / tail.length * 100;
}

/** Beta of asset vs benchmark returns. */
function computeBeta(assetRets, benchRets) {
  const n = Math.min(assetRets.length, benchRets.length);
  if (n < 2) return { beta: 1.0, correlation: 0.0, r_squared: 0.0 };
  const a = assetRets.slice(-n), b = benchRets.slice(-n);
  const ma = a.reduce((s, v) => s + v, 0) / n;
  const mb = b.reduce((s, v) => s + v, 0) / n;
  const cov  = a.reduce((s, v, i) => s + (v - ma) * (b[i] - mb), 0) / n;
  const varB = b.reduce((s, v) => s + (v - mb) ** 2, 0) / n;
  const varA = a.reduce((s, v) => s + (v - ma) ** 2, 0) / n;
  const beta = varB > 0 ? cov / varB : 1.0;
  const std  = Math.sqrt(varA) * Math.sqrt(varB);
  const corr = std > 0 ? cov / std : 0.0;
  return { beta: Math.round(beta * 10000) / 10000, correlation: Math.round(corr * 10000) / 10000, r_squared: Math.round(corr ** 2 * 10000) / 10000 };
}

async function fetchPricesByTicker(tickers, days) {
  if (!tickers.length) return {};
  const placeholders = tickers.map((_, i) => `$${i + 1}`).join(",");
  const { rows } = await pool.query(`
    SELECT s.ticker, m.close_price, m.trade_date
    FROM market_data m
    JOIN symbols s ON s.id = m.symbol_id
    WHERE s.ticker IN (${placeholders})
      AND m.trade_date >= NOW() - ($${tickers.length + 1} || ' days')::interval
    ORDER BY s.ticker, m.trade_date ASC
  `, [...tickers, days + 5]);

  const map = {};
  for (const row of rows) {
    (map[row.ticker] ??= []).push(parseFloat(row.close_price));
  }
  return map;
}

// ── GET /api/v2/risk ──────────────────────────────────────────────────────
router.get("/", requireAuth, async (req, res, next) => {
  try {
    const parsed = querySchema.safeParse(req.query);
    if (!parsed.success) {
      return res.status(400).json({ data: null, error: parsed.error.flatten(), meta: {} });
    }
    const { days, confidence, benchmark } = parsed.data;
    const cacheKey = `v2:risk:portfolio:${days}:${confidence}:${benchmark}`;

    const data = await cached(cacheKey, 120, async () => {
      // Get all tracked tickers
      const { rows: symRows } = await pool.query("SELECT ticker FROM symbols ORDER BY ticker");
      const tickers = symRows.map(r => r.ticker);
      const allTickers = [...new Set([...tickers, benchmark])];

      const priceMap  = await fetchPricesByTicker(allTickers, days);
      const retMap    = {};
      for (const [ticker, prices] of Object.entries(priceMap)) {
        retMap[ticker] = dailyReturns(prices);
      }

      const benchRets = retMap[benchmark] ?? [];
      const results   = [];

      for (const ticker of tickers) {
        const rets = retMap[ticker];
        if (!rets?.length) continue;

        const varPct  = historicalVar(rets, confidence);
        const cvarPct = historicalCVar(rets, confidence);
        const betaInfo = ticker !== benchmark ? computeBeta(rets, benchRets) : null;

        results.push({
          ticker,
          var_pct:     varPct !== null  ? Math.round(varPct  * 10000) / 10000 : null,
          cvar_pct:    cvarPct !== null ? Math.round(cvarPct * 10000) / 10000 : null,
          beta:        betaInfo?.beta        ?? null,
          correlation: betaInfo?.correlation ?? null,
          r_squared:   betaInfo?.r_squared   ?? null,
          observations: rets.length,
        });
      }

      // Correlation matrix
      const validTickers = results.map(r => r.ticker);
      const corr = {};
      for (const t1 of validTickers) {
        corr[t1] = {};
        for (const t2 of validTickers) {
          if (t1 === t2) { corr[t1][t2] = 1.0; continue; }
          const { correlation } = computeBeta(retMap[t1] ?? [], retMap[t2] ?? []);
          corr[t1][t2] = correlation;
        }
      }

      return {
        symbols: results,
        correlation_matrix: { tickers: validTickers, matrix: corr },
        params: { days, confidence, benchmark },
      };
    });

    res.json({ data, error: null, meta: {} });
  } catch (err) {
    next(err);
  }
});

// ── GET /api/v2/risk/:symbol ──────────────────────────────────────────────
router.get("/:symbol", requireAuth, async (req, res, next) => {
  try {
    const symbol = req.params.symbol.toUpperCase();
    const parsed = querySchema.safeParse(req.query);
    if (!parsed.success) {
      return res.status(400).json({ data: null, error: parsed.error.flatten(), meta: {} });
    }
    const { days, confidence, benchmark } = parsed.data;
    const cacheKey = `v2:risk:${symbol}:${days}:${confidence}`;

    const data = await cached(cacheKey, 120, async () => {
      const priceMap  = await fetchPricesByTicker([symbol, benchmark], days);
      const assetRets = dailyReturns(priceMap[symbol] ?? []);
      const benchRets = dailyReturns(priceMap[benchmark] ?? []);

      if (!assetRets.length) {
        return { symbol, error: "Insufficient price history" };
      }

      const varPct   = historicalVar(assetRets, confidence);
      const cvarPct  = historicalCVar(assetRets, confidence);
      const betaInfo = computeBeta(assetRets, benchRets);

      // Annualised volatility
      const mean    = assetRets.reduce((s, r) => s + r, 0) / assetRets.length;
      const variance = assetRets.reduce((s, r) => s + (r - mean) ** 2, 0) / assetRets.length;
      const annVol  = Math.sqrt(variance * 252) * 100;

      return {
        symbol,
        var_pct:              varPct  !== null ? Math.round(varPct  * 10000) / 10000 : null,
        cvar_pct:             cvarPct !== null ? Math.round(cvarPct * 10000) / 10000 : null,
        annualised_vol_pct:   Math.round(annVol * 100) / 100,
        beta:                 betaInfo.beta,
        correlation:          betaInfo.correlation,
        r_squared:            betaInfo.r_squared,
        benchmark,
        observations:         assetRets.length,
        params:               { days, confidence },
      };
    });

    res.json({ data, error: null, meta: { symbol } });
  } catch (err) {
    next(err);
  }
});

export default router;
