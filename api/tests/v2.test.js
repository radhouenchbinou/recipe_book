/**
 * Phase 2 Sprint 2 — API v2 route tests
 * Tests backtest, performance, rebalance, and equity endpoints.
 */

import request from "supertest";
import app from "../src/app.js";

// ── Helper: get auth token ─────────────────────────────────────────────────

let token;
beforeAll(async () => {
  const res = await request(app)
    .post("/auth/login")
    .send({ username: process.env.DEV_USERNAME ?? "admin", password: process.env.DEV_PASSWORD ?? "changeme" });
  token = res.body?.data?.token;
});

// ── /api/v2/backtest ───────────────────────────────────────────────────────

describe("GET /api/v2/backtest", () => {
  it("requires auth", async () => {
    const res = await request(app).get("/api/v2/backtest");
    expect(res.status).toBe(401);
  });

  it("returns { data, error, meta } envelope", async () => {
    const res = await request(app)
      .get("/api/v2/backtest")
      .set("Authorization", `Bearer ${token}`);
    expect([200, 503]).toContain(res.status);
    expect(res.body).toHaveProperty("data");
    expect(res.body).toHaveProperty("error");
    expect(res.body).toHaveProperty("meta");
  });
});

describe("GET /api/v2/backtest/:symbol", () => {
  it("requires auth", async () => {
    const res = await request(app).get("/api/v2/backtest/AAPL");
    expect(res.status).toBe(401);
  });

  it("returns envelope for known ticker", async () => {
    const res = await request(app)
      .get("/api/v2/backtest/AAPL")
      .set("Authorization", `Bearer ${token}`);
    expect([200, 503]).toContain(res.status);
    if (res.status === 200) {
      expect(res.body.data).toHaveProperty("symbol", "AAPL");
      expect(res.body.data).toHaveProperty("signals");
      expect(Array.isArray(res.body.data.signals)).toBe(true);
    }
  });

  it("rejects invalid date query", async () => {
    const res = await request(app)
      .get("/api/v2/backtest/AAPL?start=not-a-date")
      .set("Authorization", `Bearer ${token}`);
    expect(res.status).toBe(400);
    expect(res.body.error).toBeDefined();
  });
});

// ── /api/v2/performance ────────────────────────────────────────────────────

describe("GET /api/v2/performance", () => {
  it("requires auth", async () => {
    const res = await request(app).get("/api/v2/performance");
    expect(res.status).toBe(401);
  });

  it("returns recommendation aggregate", async () => {
    const res = await request(app)
      .get("/api/v2/performance")
      .set("Authorization", `Bearer ${token}`);
    expect([200, 503]).toContain(res.status);
    if (res.status === 200) {
      expect(res.body.data).toHaveProperty("recommendations");
      expect(res.body.data.recommendations).toHaveProperty("total");
    }
  });
});

describe("GET /api/v2/performance/:symbol", () => {
  it("requires auth", async () => {
    const res = await request(app).get("/api/v2/performance/SPY");
    expect(res.status).toBe(401);
  });

  it("returns symbol performance", async () => {
    const res = await request(app)
      .get("/api/v2/performance/SPY")
      .set("Authorization", `Bearer ${token}`);
    expect([200, 503]).toContain(res.status);
    if (res.status === 200) {
      expect(res.body.data).toHaveProperty("symbol", "SPY");
    }
  });
});

// ── /api/v2/rebalance ─────────────────────────────────────────────────────

describe("GET /api/v2/rebalance", () => {
  it("requires auth", async () => {
    const res = await request(app).get("/api/v2/rebalance");
    expect(res.status).toBe(401);
  });

  it("returns rebalance plan", async () => {
    const res = await request(app)
      .get("/api/v2/rebalance")
      .set("Authorization", `Bearer ${token}`);
    expect([200, 503]).toContain(res.status);
    if (res.status === 200) {
      expect(res.body.data).toHaveProperty("target_weights");
    }
  });
});

describe("POST /api/v2/rebalance/execute", () => {
  it("requires auth", async () => {
    const res = await request(app)
      .post("/api/v2/rebalance/execute")
      .send({ confirm: true });
    expect(res.status).toBe(401);
  });

  it("rejects missing confirm", async () => {
    const res = await request(app)
      .post("/api/v2/rebalance/execute")
      .set("Authorization", `Bearer ${token}`)
      .send({});
    expect(res.status).toBe(400);
    expect(res.body.error).toBeDefined();
  });

  it("accepts confirm:true and returns 202", async () => {
    const res = await request(app)
      .post("/api/v2/rebalance/execute")
      .set("Authorization", `Bearer ${token}`)
      .send({ confirm: true });
    expect([202, 503]).toContain(res.status);
    if (res.status === 202) {
      expect(res.body.data.status).toBe("accepted");
      expect(res.body.data.paper_trading).toBe(true);
    }
  });
});

// ── /api/v2/equity ────────────────────────────────────────────────────────

describe("GET /api/v2/equity", () => {
  it("requires auth", async () => {
    const res = await request(app).get("/api/v2/equity");
    expect(res.status).toBe(401);
  });

  it("returns equity curve", async () => {
    const res = await request(app)
      .get("/api/v2/equity?days=30")
      .set("Authorization", `Bearer ${token}`);
    expect([200, 503]).toContain(res.status);
    if (res.status === 200) {
      expect(res.body.data).toHaveProperty("equity_curve");
      expect(Array.isArray(res.body.data.equity_curve)).toBe(true);
    }
  });

  it("rejects out-of-range days param", async () => {
    const res = await request(app)
      .get("/api/v2/equity?days=999")
      .set("Authorization", `Bearer ${token}`);
    expect(res.status).toBe(400);
  });
});

describe("GET /api/v2/equity/:symbol", () => {
  it("requires auth", async () => {
    const res = await request(app).get("/api/v2/equity/AAPL");
    expect(res.status).toBe(401);
  });

  it("returns symbol equity curve", async () => {
    const res = await request(app)
      .get("/api/v2/equity/AAPL?days=30")
      .set("Authorization", `Bearer ${token}`);
    expect([200, 503]).toContain(res.status);
    if (res.status === 200) {
      expect(res.body.data.symbol).toBe("AAPL");
      expect(res.body.data).toHaveProperty("equity_curve");
    }
  });
});
