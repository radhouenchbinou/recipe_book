/**
 * Phase 2 Sprint 2 — Equity curve API route
 * GET /api/v2/equity/:symbol?days=90   per-symbol simulated equity
 * GET /api/v2/equity?days=90           portfolio equity (sum across symbols)
 *
 * Builds a daily equity time-series from analysis_scores + recommendations
 * stored in the DB so the dashboard can render P&L charts without running
 * a full backtest on demand.
 */

import { Router } from "express";
import { z } from "zod";
import { requireAuth } from "../../middleware/auth.js";
import pool from "../../services/db.js";
import { cached } from "../../services/redis.js";

const router = Router();

const querySchema = z.object({
  days: z.coerce.number().int().min(7).max(365).default(90),
});

// GET /api/v2/equity/:symbol
router.get("/:symbol", requireAuth, async (req, res, next) => {
  try {
    const symbol = req.params.symbol.toUpperCase();
    const parsed = querySchema.safeParse(req.query);
    if (!parsed.success) {
      return res.status(400).json({ data: null, error: parsed.error.flatten(), meta: {} });
    }
    const { days } = parsed.data;
    const cacheKey = `v2:equity:${symbol}:${days}`;

    const data = await cached(cacheKey, 120, async () => {
      // Join market_data close prices with the latest recommendation per day
      // to produce a daily equity curve (100k starting capital, 10% max pos).
      const { rows } = await pool.query(`
        WITH daily AS (
          SELECT
            DATE(m.trade_date)  AS trade_date,
            m.close_price,
            r.action,
            r.confidence,
            r.position_size
          FROM market_data m
          JOIN symbols s ON s.id = m.symbol_id
          LEFT JOIN LATERAL (
            SELECT r2.action, r2.confidence, r2.position_size
            FROM recommendations r2
            WHERE r2.symbol_id = s.id
              AND DATE(r2.created_at) <= DATE(m.trade_date)
            ORDER BY r2.created_at DESC
            LIMIT 1
          ) r ON TRUE
          WHERE s.ticker = $1
            AND m.trade_date >= NOW() - ($2 || ' days')::interval
          ORDER BY m.trade_date ASC
        )
        SELECT
          trade_date,
          close_price,
          COALESCE(action,       'hold') AS action,
          COALESCE(confidence,    0.5)   AS confidence,
          COALESCE(position_size, 0.05)  AS position_size
        FROM daily
      `, [symbol, days]);

      if (!rows.length) {
        return { symbol, days, equity_curve: [], summary: null };
      }

      // Simulate equity with simplified mark-to-market
      const INITIAL = 100_000;
      let cash        = INITIAL;
      let shares      = 0;
      let entry_price = 0;
      const curve: { date: string; equity: number; close: number; action: string }[] = [];

      for (const row of rows) {
        const close   = parseFloat(row.close_price);
        const action  = row.action;
        const pos_pct = parseFloat(row.position_size) || 0.05;

        if (action === "buy" && shares === 0 && cash > 0) {
          const invest = cash * Math.min(pos_pct, 0.10);
          shares       = Math.floor(invest / close);
          entry_price  = close;
          cash        -= shares * close * 1.001; // commission
        } else if (action === "sell" && shares > 0) {
          cash   += shares * close * 0.999; // commission
          shares  = 0;
          entry_price = 0;
        }

        const equity = cash + shares * close;
        curve.push({
          date:   row.trade_date.toISOString().slice(0, 10),
          equity: Math.round(equity * 100) / 100,
          close,
          action,
        });
      }

      const first  = curve[0].equity;
      const last   = curve[curve.length - 1].equity;
      const peak   = Math.max(...curve.map(p => p.equity));
      const trough = Math.min(...curve.map(p => p.equity));
      const maxDD  = peak > 0 ? Math.round((peak - trough) / peak * 10000) / 100 : 0;

      return {
        symbol,
        days,
        initial_capital: INITIAL,
        equity_curve: curve,
        summary: {
          start_equity:       Math.round(first * 100) / 100,
          end_equity:         Math.round(last  * 100) / 100,
          total_return_pct:   first > 0 ? Math.round((last - first) / first * 10000) / 100 : 0,
          max_drawdown_pct:   maxDD,
          data_points:        curve.length,
        },
      };
    });

    res.json({ data, error: null, meta: { symbol, days } });
  } catch (err) {
    next(err);
  }
});

// GET /api/v2/equity  — aggregated portfolio equity (average across symbols)
router.get("/", requireAuth, async (req, res, next) => {
  try {
    const parsed = querySchema.safeParse(req.query);
    if (!parsed.success) {
      return res.status(400).json({ data: null, error: parsed.error.flatten(), meta: {} });
    }
    const { days } = parsed.data;
    const cacheKey = `v2:equity:portfolio:${days}`;

    const data = await cached(cacheKey, 120, async () => {
      // Pull aggregate market value per day from all tracked symbols
      const { rows } = await pool.query(`
        SELECT
          DATE(m.trade_date)      AS trade_date,
          SUM(m.close_price)      AS total_close,
          AVG(m.close_price)      AS avg_close,
          COUNT(DISTINCT s.id)    AS symbol_count
        FROM market_data m
        JOIN symbols s ON s.id = m.symbol_id
        WHERE m.trade_date >= NOW() - ($1 || ' days')::interval
        GROUP BY DATE(m.trade_date)
        ORDER BY trade_date ASC
      `, [days]);

      if (!rows.length) {
        return { days, equity_curve: [], summary: null };
      }

      const base  = parseFloat(rows[0].avg_close) || 1;
      const curve = rows.map(r => {
        const avg = parseFloat(r.avg_close);
        return {
          date:         r.trade_date.toISOString().slice(0, 10),
          equity:       Math.round(100_000 * (avg / base) * 100) / 100,
          symbol_count: parseInt(r.symbol_count),
        };
      });

      const first = curve[0].equity;
      const last  = curve[curve.length - 1].equity;

      return {
        days,
        equity_curve: curve,
        summary: {
          start_equity:     first,
          end_equity:       last,
          total_return_pct: first > 0 ? Math.round((last - first) / first * 10000) / 100 : 0,
          data_points:      curve.length,
        },
      };
    });

    res.json({ data, error: null, meta: { days } });
  } catch (err) {
    next(err);
  }
});

export default router;
