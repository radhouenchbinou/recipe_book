/**
 * k6 Load Test — Trading Bot API
 * Task S5-T2-001
 *
 * Targets: 100 concurrent users, p99 < 500ms, error rate < 1%
 *
 * Run:
 *   k6 run infra/k6/load-test.js \
 *     -e BASE_URL=http://localhost:3000 \
 *     -e USERNAME=admin \
 *     -e PASSWORD=changeme
 */

import http from "k6/http";
import { check, group, sleep } from "k6";
import { Rate, Trend } from "k6/metrics";

// ── Custom metrics ──────────────────────────────────────────────────────────
const errorRate       = new Rate("errors");
const portfolioTrend  = new Trend("portfolio_duration",     true);
const recsTrend       = new Trend("recommendations_duration", true);
const marketDataTrend = new Trend("market_data_duration",   true);
const alertsTrend     = new Trend("alerts_duration",        true);

// ── Test options ────────────────────────────────────────────────────────────
export const options = {
  scenarios: {
    // Ramp up to 100 users, hold 2 min, ramp down
    steady_load: {
      executor: "ramping-vus",
      startVUs: 0,
      stages: [
        { duration: "30s", target: 50  },   // warm up
        { duration: "2m",  target: 100 },   // target load
        { duration: "30s", target: 0   },   // ramp down
      ],
    },
  },
  thresholds: {
    // Gate G4/G5 criteria
    http_req_duration:           ["p(99)<500", "p(95)<300"],
    http_req_failed:             ["rate<0.01"],
    errors:                      ["rate<0.01"],
    portfolio_duration:          ["p(99)<500"],
    recommendations_duration:    ["p(99)<500"],
    market_data_duration:        ["p(99)<500"],
    alerts_duration:             ["p(99)<500"],
  },
};

const BASE_URL = __ENV.BASE_URL || "http://localhost:3000";
const USERNAME = __ENV.USERNAME || "admin";
const PASSWORD = __ENV.PASSWORD || "changeme";

// ── Setup: get auth token ───────────────────────────────────────────────────
export function setup() {
  const res = http.post(
    `${BASE_URL}/auth/login`,
    JSON.stringify({ username: USERNAME, password: PASSWORD }),
    { headers: { "Content-Type": "application/json" } }
  );
  if (res.status !== 200) {
    throw new Error(`Login failed: ${res.status} ${res.body}`);
  }
  return { token: res.json("data.token") };
}

// ── Main virtual user scenario ──────────────────────────────────────────────
export default function (data) {
  const headers = {
    Authorization: `Bearer ${data.token}`,
    "Content-Type": "application/json",
  };

  group("health", () => {
    const res = http.get(`${BASE_URL}/health`);
    check(res, { "health 200": (r) => r.status === 200 });
    errorRate.add(res.status !== 200);
  });

  sleep(0.5);

  group("portfolio", () => {
    const res = http.get(`${BASE_URL}/api/v1/portfolio`, { headers });
    portfolioTrend.add(res.timings.duration);
    const ok = check(res, {
      "portfolio 200": (r) => r.status === 200,
      "portfolio has data": (r) => r.json("data") !== null,
    });
    errorRate.add(!ok);
  });

  sleep(0.3);

  group("positions", () => {
    const res = http.get(`${BASE_URL}/api/v1/portfolio/positions`, { headers });
    check(res, { "positions 200": (r) => r.status === 200 });
    errorRate.add(res.status !== 200);
  });

  sleep(0.3);

  group("recommendations", () => {
    const res = http.get(
      `${BASE_URL}/api/v1/recommendations?limit=20&source=all`,
      { headers }
    );
    recsTrend.add(res.timings.duration);
    const ok = check(res, {
      "recs 200": (r) => r.status === 200,
      "recs has array": (r) => Array.isArray(r.json("data")),
    });
    errorRate.add(!ok);
  });

  sleep(0.3);

  // Rotate through symbols
  const symbols = ["SPY", "QQQ", "GLD", "AAPL", "MSFT", "NVDA"];
  const symbol = symbols[Math.floor(Math.random() * symbols.length)];

  group("market_data", () => {
    const res = http.get(
      `${BASE_URL}/api/v1/market-data/${symbol}?days=30`,
      { headers }
    );
    marketDataTrend.add(res.timings.duration);
    check(res, { "market_data 200 or 404": (r) => [200, 404].includes(r.status) });
    errorRate.add(![200, 404].includes(res.status));
  });

  sleep(0.3);

  group("alerts", () => {
    const res = http.get(`${BASE_URL}/api/v1/alerts`, { headers });
    alertsTrend.add(res.timings.duration);
    check(res, { "alerts 200": (r) => r.status === 200 });
    errorRate.add(res.status !== 200);
  });

  sleep(1);
}

export function teardown(data) {
  console.log("Load test complete. Token used:", data.token ? "✓" : "✗");
}
