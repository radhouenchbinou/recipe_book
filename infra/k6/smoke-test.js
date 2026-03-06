/**
 * k6 Smoke Test — quick sanity check before load test
 * 1 VU, 30 seconds — verifies all endpoints are reachable
 *
 * Run: k6 run infra/k6/smoke-test.js -e BASE_URL=http://localhost:3000
 */

import http from "k6/http";
import { check, group } from "k6";

export const options = {
  vus: 1,
  duration: "30s",
  thresholds: {
    http_req_failed:   ["rate==0"],
    http_req_duration: ["p(99)<1000"],
  },
};

const BASE_URL = __ENV.BASE_URL || "http://localhost:3000";
const USERNAME = __ENV.USERNAME || "admin";
const PASSWORD = __ENV.PASSWORD || "changeme";

export function setup() {
  const res = http.post(
    `${BASE_URL}/auth/login`,
    JSON.stringify({ username: USERNAME, password: PASSWORD }),
    { headers: { "Content-Type": "application/json" } }
  );
  check(res, { "login 200": (r) => r.status === 200 });
  return { token: res.json("data.token") };
}

export default function (data) {
  const h = { Authorization: `Bearer ${data.token}` };

  group("smoke", () => {
    check(http.get(`${BASE_URL}/health`),                               { "health":   (r) => r.status === 200 });
    check(http.get(`${BASE_URL}/api/v1/portfolio`, { headers: h }),     { "portfolio": (r) => r.status === 200 });
    check(http.get(`${BASE_URL}/api/v1/recommendations`, { headers: h }),{ "recs":    (r) => r.status === 200 });
    check(http.get(`${BASE_URL}/api/v1/alerts`, { headers: h }),        { "alerts":   (r) => r.status === 200 });
  });
}
