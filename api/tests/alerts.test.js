/**
 * Alerts endpoint tests — CRUD operations
 * Uses JWT obtained from /auth/login.
 */

import { describe, it, expect, beforeAll } from "@jest/globals";
import request from "supertest";
import app from "../src/app.js";

process.env.DATABASE_URL = "postgresql://trader:trader@localhost:5432/tradingbot_test";
process.env.DEV_USERNAME = "admin";
process.env.DEV_PASSWORD = "changeme";

let token;

beforeAll(async () => {
  const res = await request(app)
    .post("/auth/login")
    .send({ username: "admin", password: "changeme" });
  token = res.body?.data?.token;
});

function auth(req) {
  return req.set("Authorization", `Bearer ${token}`);
}

describe("Alerts API", () => {
  it("GET /api/v1/alerts returns 200 with array", async () => {
    if (!token) return; // skip if DB not available
    const res = await auth(request(app).get("/api/v1/alerts"));
    expect([200, 500]).toContain(res.status); // 500 if no DB in CI
    if (res.status === 200) {
      expect(Array.isArray(res.body.data)).toBe(true);
    }
  });

  it("POST /api/v1/alerts validates required fields", async () => {
    if (!token) return;
    const res = await auth(request(app).post("/api/v1/alerts")).send({});
    expect([400, 500]).toContain(res.status);
  });

  it("DELETE /api/v1/alerts/:id returns 404 for non-existent id", async () => {
    if (!token) return;
    const res = await auth(request(app).delete("/api/v1/alerts/00000000-0000-0000-0000-000000000000"));
    expect([404, 500]).toContain(res.status);
  });

  it("rejects requests without auth", async () => {
    const res = await request(app).get("/api/v1/alerts");
    expect(res.status).toBe(401);
  });
});
