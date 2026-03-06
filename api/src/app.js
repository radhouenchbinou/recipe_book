/**
 * Trading Bot REST API — Express entry point
 * Task S1-T4-001
 */

import "dotenv/config";
import express from "express";
import cors from "cors";
import helmet from "helmet";
import rateLimit from "express-rate-limit";

import { logger } from "./middleware/logger.js";
import { errorHandler } from "./middleware/errorHandler.js";
import healthRouter          from "./routes/health.js";
import authRouter            from "./routes/auth.js";
import portfolioRouter       from "./routes/portfolio.js";
import recommendationsRouter from "./routes/recommendations.js";
import marketDataRouter      from "./routes/marketData.js";
import alertsRouter          from "./routes/alerts.js";
import backtestRouter        from "./routes/v2/backtest.js";
import performanceRouter     from "./routes/v2/performance.js";
import rebalanceRouter       from "./routes/v2/rebalance.js";
import equityRouter          from "./routes/v2/equity.js";

const app = express();
const PORT = process.env.API_PORT ?? 3000;

// ── Security middleware ────────────────────────────────────────────────────
app.use(helmet());
app.use(cors({ origin: process.env.CORS_ORIGIN ?? "*" }));
app.use(rateLimit({ windowMs: 60_000, max: 300, standardHeaders: true }));

// ── Body parsing ───────────────────────────────────────────────────────────
app.use(express.json({ limit: "1mb" }));

// ── Request logging ────────────────────────────────────────────────────────
app.use(logger);

// ── Routes ─────────────────────────────────────────────────────────────────
app.use("/health",                    healthRouter);
app.use("/auth",                      authRouter);
app.use("/api/v1/portfolio",          portfolioRouter);
app.use("/api/v1/recommendations",    recommendationsRouter);
app.use("/api/v1/market-data",        marketDataRouter);
app.use("/api/v1/alerts",             alertsRouter);
app.use("/api/v2/backtest",          backtestRouter);
app.use("/api/v2/performance",       performanceRouter);
app.use("/api/v2/rebalance",         rebalanceRouter);
app.use("/api/v2/equity",            equityRouter);

// ── 404 ────────────────────────────────────────────────────────────────────
app.use((_req, res) => {
  res.status(404).json({ data: null, error: "Not found", meta: {} });
});

// ── Error handler ──────────────────────────────────────────────────────────
app.use(errorHandler);

// ── Start ──────────────────────────────────────────────────────────────────
if (process.env.NODE_ENV !== "test") {
  app.listen(PORT, () => {
    console.log(JSON.stringify({ level: "info", msg: "api.started", port: PORT }));
  });
}

export default app;
