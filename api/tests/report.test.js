/**
 * Phase 3 Sprint 3 — /api/v2/report route tests
 * Covers trades, pnl, and accuracy endpoints.
 */

import request from "supertest";
import app from "../src/app.js";

let token;
beforeAll(async () => {
  const res = await request(app)
    .post("/auth/login")
    .send({
      username: process.env.DEV_USERNAME ?? "admin",
      password: process.env.DEV_PASSWORD ?? "changeme",
    });
  token = res.body?.data?.token;
});

// ── /api/v2/report/trades ─────────────────────────────────────────────────

describe("GET /api/v2/report/trades", () => {
  it("requires auth", async () => {
    const res = await request(app).get("/api/v2/report/trades");
    expect(res.status).toBe(401);
  });

  it("returns { data, error, meta } envelope", async () => {
    const res = await request(app)
      .get("/api/v2/report/trades")
      .set("Authorization", `Bearer ${token}`);
    expect([200, 503]).toContain(res.status);
    expect(res.body).toHaveProperty("data");
    expect(res.body).toHaveProperty("error");
    expect(res.body).toHaveProperty("meta");
  });

  it("returns summary and rows keys on 200", async () => {
    const res = await request(app)
      .get("/api/v2/report/trades")
      .set("Authorization", `Bearer ${token}`);
    if (res.status === 200) {
      expect(res.body.data).toHaveProperty("summary");
      expect(res.body.data).toHaveProperty("rows");
      expect(Array.isArray(res.body.data.rows)).toBe(true);
    }
  });

  it("filters by symbol param", async () => {
    const res = await request(app)
      .get("/api/v2/report/trades?symbol=AAPL")
      .set("Authorization", `Bearer ${token}`);
    expect([200, 503]).toContain(res.status);
    if (res.status === 200) {
      res.body.data.rows.forEach((r) => expect(r.symbol).toBe("AAPL"));
    }
  });

  it("filters by status param", async () => {
    const res = await request(app)
      .get("/api/v2/report/trades?status=filled")
      .set("Authorization", `Bearer ${token}`);
    expect([200, 503]).toContain(res.status);
    if (res.status === 200) {
      res.body.data.rows.forEach((r) => expect(r.status).toBe("filled"));
    }
  });

  it("rejects invalid days param", async () => {
    const res = await request(app)
      .get("/api/v2/report/trades?days=0")
      .set("Authorization", `Bearer ${token}`);
    expect(res.status).toBe(400);
  });

  it("rejects out-of-range limit", async () => {
    const res = await request(app)
      .get("/api/v2/report/trades?limit=9999")
      .set("Authorization", `Bearer ${token}`);
    expect(res.status).toBe(400);
  });

  it("accepts format=csv and returns csv content-type", async () => {
    const res = await request(app)
      .get("/api/v2/report/trades?format=csv")
      .set("Authorization", `Bearer ${token}`);
    if (res.status === 200) {
      expect(res.headers["content-type"]).toMatch(/text\/csv/);
      expect(res.headers["content-disposition"]).toMatch(/attachment/);
    }
  });

  it("rejects invalid format param", async () => {
    const res = await request(app)
      .get("/api/v2/report/trades?format=xml")
      .set("Authorization", `Bearer ${token}`);
    expect(res.status).toBe(400);
  });
});

// ── /api/v2/report/pnl ───────────────────────────────────────────────────

describe("GET /api/v2/report/pnl", () => {
  it("requires auth", async () => {
    const res = await request(app).get("/api/v2/report/pnl");
    expect(res.status).toBe(401);
  });

  it("returns { data, error, meta } envelope", async () => {
    const res = await request(app)
      .get("/api/v2/report/pnl")
      .set("Authorization", `Bearer ${token}`);
    expect([200, 503]).toContain(res.status);
    expect(res.body).toHaveProperty("data");
    expect(res.body).toHaveProperty("error");
    expect(res.body).toHaveProperty("meta");
  });

  it("returns summary with symbols_traded and total_realised_pl", async () => {
    const res = await request(app)
      .get("/api/v2/report/pnl")
      .set("Authorization", `Bearer ${token}`);
    if (res.status === 200) {
      expect(res.body.data.summary).toHaveProperty("symbols_traded");
      expect(res.body.data.summary).toHaveProperty("total_realised_pl");
    }
  });

  it("accepts days=90", async () => {
    const res = await request(app)
      .get("/api/v2/report/pnl?days=90")
      .set("Authorization", `Bearer ${token}`);
    expect([200, 503]).toContain(res.status);
    if (res.status === 200) {
      expect(res.body.meta.filters.days).toBe(90);
    }
  });

  it("accepts format=csv", async () => {
    const res = await request(app)
      .get("/api/v2/report/pnl?format=csv")
      .set("Authorization", `Bearer ${token}`);
    if (res.status === 200) {
      expect(res.headers["content-type"]).toMatch(/text\/csv/);
    }
  });
});

// ── /api/v2/report/accuracy ──────────────────────────────────────────────

describe("GET /api/v2/report/accuracy", () => {
  it("requires auth", async () => {
    const res = await request(app).get("/api/v2/report/accuracy");
    expect(res.status).toBe(401);
  });

  it("returns { data, error, meta } envelope", async () => {
    const res = await request(app)
      .get("/api/v2/report/accuracy")
      .set("Authorization", `Bearer ${token}`);
    expect([200, 503]).toContain(res.status);
    expect(res.body).toHaveProperty("data");
    expect(res.body).toHaveProperty("error");
    expect(res.body).toHaveProperty("meta");
  });

  it("returns groups count on 200", async () => {
    const res = await request(app)
      .get("/api/v2/report/accuracy")
      .set("Authorization", `Bearer ${token}`);
    if (res.status === 200) {
      expect(res.body.data).toHaveProperty("groups");
      expect(typeof res.body.data.groups).toBe("number");
      expect(Array.isArray(res.body.data.rows)).toBe(true);
    }
  });

  it("rejects invalid days", async () => {
    const res = await request(app)
      .get("/api/v2/report/accuracy?days=400")
      .set("Authorization", `Bearer ${token}`);
    expect(res.status).toBe(400);
  });

  it("accepts format=csv", async () => {
    const res = await request(app)
      .get("/api/v2/report/accuracy?format=csv")
      .set("Authorization", `Bearer ${token}`);
    if (res.status === 200) {
      expect(res.headers["content-type"]).toMatch(/text\/csv/);
    }
  });
});
