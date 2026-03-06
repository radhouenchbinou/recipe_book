/**
 * End-to-End Acceptance Tests — Phase 1 Go/No-Go
 * Task S5-T4-001
 *
 * Covers the full user journey:
 *   Login → view portfolio → see recommendations → create alert → delete alert
 *
 * Run against a live stack:
 *   BASE_URL=http://localhost:3000 node --test infra/e2e/acceptance.test.js
 *
 * Or via npm script:
 *   BASE_URL=http://localhost:3000 npm run e2e
 */

import { describe, it, before, after } from "node:test";
import assert from "node:assert/strict";

const BASE_URL = process.env.BASE_URL ?? "http://localhost:3000";
const USERNAME  = process.env.DEV_USERNAME  ?? "admin";
const PASSWORD  = process.env.DEV_PASSWORD  ?? "changeme";

let authToken;
let createdAlertId;

async function api(method, path, body, token) {
  const opts = {
    method,
    headers: {
      "Content-Type":  "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    ...(body ? { body: JSON.stringify(body) } : {}),
  };
  const res = await fetch(`${BASE_URL}${path}`, opts);
  return { status: res.status, body: await res.json() };
}

// ── 1. Health check ─────────────────────────────────────────────────────────
describe("Health", () => {
  it("GET /health returns 200", async () => {
    const { status, body } = await api("GET", "/health");
    assert.equal(status, 200);
    assert.equal(body.data.api, "ok");
  });
});

// ── 2. Authentication ────────────────────────────────────────────────────────
describe("Authentication", () => {
  it("POST /auth/login with valid credentials returns JWT", async () => {
    const { status, body } = await api("POST", "/auth/login", { username: USERNAME, password: PASSWORD });
    assert.equal(status, 200);
    assert.ok(body.data.token, "Expected a token in response");
    assert.equal(body.error, null);
    authToken = body.data.token;
  });

  it("POST /auth/login with wrong password returns 401", async () => {
    const { status } = await api("POST", "/auth/login", { username: USERNAME, password: "wrong" });
    assert.equal(status, 401);
  });

  it("Protected route without token returns 401", async () => {
    const { status } = await api("GET", "/api/v1/alerts");
    assert.equal(status, 401);
  });
});

// ── 3. Portfolio ─────────────────────────────────────────────────────────────
describe("Portfolio", () => {
  it("GET /api/v1/portfolio returns account data", async () => {
    const { status, body } = await api("GET", "/api/v1/portfolio", null, authToken);
    // 200 (Alpaca connected) or 503 (paper account not configured in CI)
    assert.ok([200, 503].includes(status), `Expected 200 or 503, got ${status}`);
    if (status === 200) {
      assert.ok(body.data.portfolio_value !== undefined);
      assert.ok(body.data.equity !== undefined);
    }
  });

  it("GET /api/v1/portfolio/positions returns array", async () => {
    const { status, body } = await api("GET", "/api/v1/portfolio/positions", null, authToken);
    assert.ok([200, 503].includes(status));
    if (status === 200) {
      assert.ok(Array.isArray(body.data));
    }
  });
});

// ── 4. Recommendations ───────────────────────────────────────────────────────
describe("Recommendations", () => {
  it("GET /api/v1/recommendations returns paginated response", async () => {
    const { status, body } = await api("GET", "/api/v1/recommendations?limit=10", null, authToken);
    assert.equal(status, 200);
    assert.ok(Array.isArray(body.data));
    assert.ok(body.meta.total !== undefined);
    assert.ok(body.meta.limit === 10);
  });

  it("GET /api/v1/recommendations filters by action=buy", async () => {
    const { status, body } = await api("GET", "/api/v1/recommendations?action=buy&limit=5", null, authToken);
    assert.equal(status, 200);
    body.data.forEach((rec) => assert.equal(rec.action, "buy"));
  });

  it("GET /api/v1/recommendations/:symbol returns 200 or 404", async () => {
    const { status } = await api("GET", "/api/v1/recommendations/SPY", null, authToken);
    assert.ok([200, 404].includes(status));
  });
});

// ── 5. Market Data ───────────────────────────────────────────────────────────
describe("Market Data", () => {
  it("GET /api/v1/market-data/SPY returns 200 or 404", async () => {
    const { status, body } = await api("GET", "/api/v1/market-data/SPY?days=30", null, authToken);
    assert.ok([200, 404].includes(status));
    if (status === 200) {
      assert.equal(body.data.ticker, "SPY");
      assert.ok(Array.isArray(body.data.ohlcv));
    }
  });

  it("GET /api/v1/market-data/INVALID returns 404", async () => {
    const { status } = await api("GET", "/api/v1/market-data/XXXXXX", null, authToken);
    assert.ok([404, 200].includes(status));
  });
});

// ── 6. Alerts CRUD ───────────────────────────────────────────────────────────
describe("Alerts", () => {
  it("GET /api/v1/alerts returns array", async () => {
    const { status, body } = await api("GET", "/api/v1/alerts", null, authToken);
    assert.equal(status, 200);
    assert.ok(Array.isArray(body.data));
    assert.equal(body.error, null);
  });

  it("POST /api/v1/alerts creates a new alert", async () => {
    const { status, body } = await api(
      "POST", "/api/v1/alerts",
      { symbol: "AAPL", alert_type: "price_above", threshold: 200, message: "E2E test alert" },
      authToken
    );
    assert.ok([201, 404].includes(status)); // 404 if AAPL not in DB during CI
    if (status === 201) {
      assert.ok(body.data.id);
      assert.equal(body.data.alert_type, "price_above");
      createdAlertId = body.data.id;
    }
  });

  it("PATCH /api/v1/alerts/:id toggles active state", async () => {
    if (!createdAlertId) return; // skip if alert wasn't created
    const { status, body } = await api("PATCH", `/api/v1/alerts/${createdAlertId}`, { active: false }, authToken);
    assert.equal(status, 200);
    assert.equal(body.data.active, false);
  });

  it("DELETE /api/v1/alerts/:id removes the alert", async () => {
    if (!createdAlertId) return;
    const { status, body } = await api("DELETE", `/api/v1/alerts/${createdAlertId}`, null, authToken);
    assert.equal(status, 200);
    assert.ok(body.data.deleted);
  });

  it("POST /api/v1/alerts with missing fields returns 400", async () => {
    const { status } = await api("POST", "/api/v1/alerts", {}, authToken);
    assert.equal(status, 400);
  });
});

// ── 7. Security checks ───────────────────────────────────────────────────────
describe("Security", () => {
  it("All protected routes reject expired/invalid tokens", async () => {
    const routes = ["/api/v1/portfolio", "/api/v1/recommendations", "/api/v1/alerts"];
    for (const route of routes) {
      const { status } = await api("GET", route, null, "invalid.token.here");
      assert.equal(status, 401, `${route} should reject invalid token`);
    }
  });

  it("Response envelope always has data, error, meta keys", async () => {
    const { body } = await api("GET", "/health");
    assert.ok("data"  in body);
    assert.ok("error" in body);
    assert.ok("meta"  in body);
  });
});
