/**
 * GET /health — liveness + readiness probe.
 */

import { Router } from "express";
import pg from "pg";
import { createClient } from "ioredis";

const router = Router();

router.get("/", async (_req, res) => {
  const checks = {
    api: "ok",
    postgres: "unknown",
    redis: "unknown",
  };

  // Postgres
  const pool = new pg.Pool({ connectionString: process.env.DATABASE_URL });
  try {
    await pool.query("SELECT 1");
    checks.postgres = "ok";
  } catch {
    checks.postgres = "error";
  } finally {
    await pool.end();
  }

  // Redis
  const redis = new createClient(process.env.REDIS_URL ?? "redis://localhost:6379");
  try {
    await redis.ping();
    checks.redis = "ok";
  } catch {
    checks.redis = "error";
  } finally {
    redis.disconnect();
  }

  const allOk = Object.values(checks).every((v) => v === "ok");
  res.status(allOk ? 200 : 503).json({
    data: checks,
    error: allOk ? null : "One or more dependencies unhealthy",
    meta: { ts: new Date().toISOString() },
  });
});

export default router;
