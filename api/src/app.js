/**
 * Trading Bot REST API — Express entry point
 */

import "dotenv/config";
import { createServer } from "http";
import express from "express";
import cors from "cors";
import helmet from "helmet";
import rateLimit from "express-rate-limit";
import cookieParser from "cookie-parser";
import { Server as IOServer } from "socket.io";
import jwt from "jsonwebtoken";

import { logger } from "./middleware/logger.js";
import { errorHandler } from "./middleware/errorHandler.js";
import { requireAuth } from "./middleware/auth.js";
import healthRouter          from "./routes/health.js";
import authRouter            from "./routes/auth.js";
import portfolioRouter       from "./routes/portfolio.js";
import recommendationsRouter from "./routes/recommendations.js";
import marketDataRouter      from "./routes/marketData.js";
import alertsRouter          from "./routes/alerts.js";
import settingsRouter        from "./routes/settings.js";

const app = express();
const httpServer = createServer(app);
const PORT = process.env.API_PORT ?? 3000;
const JWT_SECRET = process.env.JWT_SECRET ?? "dev-secret-change-in-prod";

// ── Security middleware ────────────────────────────────────────────────────
app.use(helmet());
app.use(cors({ origin: process.env.CORS_ORIGIN ?? "*", credentials: true }));

// Global rate limit per IP
app.use(rateLimit({ windowMs: 60_000, max: 300, standardHeaders: true }));

// Per-user rate limit on authenticated API routes (applied after requireAuth)
const userLimiter = rateLimit({
  windowMs: 60_000,
  max: 100,
  keyGenerator: (req) => req.user?.sub?.toString() ?? req.ip,
  standardHeaders: true,
});

// ── Body / cookie parsing ──────────────────────────────────────────────────
app.use(express.json({ limit: "1mb" }));
app.use(cookieParser());

// ── Request logging ────────────────────────────────────────────────────────
app.use(logger);

// ── Routes ─────────────────────────────────────────────────────────────────
app.use("/health",                    healthRouter);
app.use("/auth",                      authRouter);
app.use("/api/v1/portfolio",          requireAuth, userLimiter, portfolioRouter);
app.use("/api/v1/recommendations",    requireAuth, userLimiter, recommendationsRouter);
app.use("/api/v1/market-data",        requireAuth, userLimiter, marketDataRouter);
app.use("/api/v1/alerts",             requireAuth, userLimiter, alertsRouter);
app.use("/api/v1/settings",           requireAuth, userLimiter, settingsRouter);

// ── 404 ────────────────────────────────────────────────────────────────────
app.use((_req, res) => {
  res.status(404).json({ data: null, error: "Not found", meta: {} });
});

// ── Error handler ──────────────────────────────────────────────────────────
app.use(errorHandler);

// ── Socket.io ──────────────────────────────────────────────────────────────
export const io = new IOServer(httpServer, {
  cors: { origin: process.env.CORS_ORIGIN ?? "*", credentials: true },
});

// Authenticate Socket.io connections via JWT handshake token
io.use((socket, next) => {
  const token = socket.handshake.auth?.token;
  if (!token) return next(new Error("Missing auth token"));
  try {
    socket.user = jwt.verify(token, JWT_SECRET);
    next();
  } catch {
    next(new Error("Invalid auth token"));
  }
});

io.on("connection", (socket) => {
  // Clients join rooms by name to receive targeted events
  socket.on("join", (room) => socket.join(room));
});

// ── Start ──────────────────────────────────────────────────────────────────
if (process.env.NODE_ENV !== "test") {
  httpServer.listen(PORT, async () => {
    console.log(JSON.stringify({ level: "info", msg: "api.started", port: PORT }));

    // Start RabbitMQ consumer (non-fatal if RabbitMQ unavailable at boot)
    try {
      const { startConsumer } = await import("./consumer.js");
      await startConsumer();
      console.log(JSON.stringify({ level: "info", msg: "rabbitmq.consumer.started" }));
    } catch (err) {
      console.log(JSON.stringify({ level: "warn", msg: "rabbitmq.consumer.failed", error: err.message }));
    }
  });
}

export default app;
