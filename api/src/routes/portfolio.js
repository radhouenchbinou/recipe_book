/**
 * GET /api/v1/portfolio  — account summary
 * GET /api/v1/portfolio/positions — open positions
 *
 * Task S4-T1-001
 */

import { Router } from "express";
import { requireAuth } from "../middleware/auth.js";
import { cached } from "../services/redis.js";

const router = Router();
router.use(requireAuth);

const ALPACA_BASE = process.env.ALPACA_BASE_URL ?? "https://paper-api.alpaca.markets";
const ALPACA_KEY  = process.env.ALPACA_API_KEY ?? "";
const ALPACA_SEC  = process.env.ALPACA_SECRET_KEY ?? "";
const CACHE_TTL   = 30; // seconds

function alpacaHeaders() {
  return {
    "APCA-API-KEY-ID":     ALPACA_KEY,
    "APCA-API-SECRET-KEY": ALPACA_SEC,
    "Content-Type":        "application/json",
  };
}

async function fetchAlpaca(path) {
  const res = await fetch(`${ALPACA_BASE}${path}`, { headers: alpacaHeaders() });
  if (!res.ok) {
    const text = await res.text();
    const err = new Error(`Alpaca error ${res.status}: ${text}`);
    err.status = res.status === 403 ? 503 : res.status;
    throw err;
  }
  return res.json();
}

/** GET /api/v1/portfolio */
router.get("/", async (req, res, next) => {
  try {
    const account = await cached("portfolio:account", CACHE_TTL, () =>
      fetchAlpaca("/v2/account")
    );
    res.json({
      data: {
        account_id:      account.id,
        equity:          parseFloat(account.equity),
        cash:            parseFloat(account.cash),
        buying_power:    parseFloat(account.buying_power),
        portfolio_value: parseFloat(account.portfolio_value),
        day_pl:          parseFloat(account.equity) - parseFloat(account.last_equity),
        day_pl_pct:      ((parseFloat(account.equity) - parseFloat(account.last_equity)) / parseFloat(account.last_equity)) * 100,
        is_paper:        ALPACA_BASE.includes("paper"),
      },
      error: null,
      meta: { cached_ttl: CACHE_TTL },
    });
  } catch (err) {
    next(err);
  }
});

/** GET /api/v1/portfolio/positions */
router.get("/positions", async (req, res, next) => {
  try {
    const positions = await cached("portfolio:positions", CACHE_TTL, () =>
      fetchAlpaca("/v2/positions")
    );
    res.json({
      data: positions.map((p) => ({
        symbol:         p.symbol,
        qty:            parseFloat(p.qty),
        market_value:   parseFloat(p.market_value),
        cost_basis:     parseFloat(p.cost_basis),
        unrealized_pl:  parseFloat(p.unrealized_pl),
        unrealized_pct: parseFloat(p.unrealized_plpc) * 100,
        current_price:  parseFloat(p.current_price),
        side:           p.side,
      })),
      error: null,
      meta: { count: positions.length, cached_ttl: CACHE_TTL },
    });
  } catch (err) {
    next(err);
  }
});

export default router;
