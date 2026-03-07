/**
 * Auth endpoint tests — register, login, refresh, logout, RBAC
 */

import { describe, it, expect, beforeEach, jest } from "@jest/globals";
import request from "supertest";
import app from "../src/app.js";

// Mock pg pool so tests don't require a live DB
jest.mock("../src/services/db.js", () => ({
  default: { query: jest.fn() },
}));

import pool from "../src/services/db.js";

process.env.JWT_SECRET = "test-secret";
process.env.NODE_ENV = "test";

const MOCK_USER = {
  id: 1, username: "alice", email: "alice@example.com", role: "trader",
  password_hash: "$2a$12$demohashedpassword",  // bcrypt hash placeholder
};

describe("POST /auth/register", () => {
  it("returns 400 for missing fields", async () => {
    const res = await request(app).post("/auth/register").send({ username: "x" });
    expect(res.status).toBe(400);
  });

  it("returns 400 for short password", async () => {
    const res = await request(app)
      .post("/auth/register")
      .send({ username: "alice", email: "alice@test.com", password: "short" });
    expect(res.status).toBe(400);
  });
});

describe("POST /auth/login", () => {
  it("returns 400 for missing fields", async () => {
    const res = await request(app).post("/auth/login").send({});
    expect(res.status).toBe(400);
  });

  it("returns 401 when user not found in DB", async () => {
    pool.query.mockResolvedValueOnce({ rows: [] });
    const res = await request(app)
      .post("/auth/login")
      .send({ username: "ghost", password: "password123" });
    expect(res.status).toBe(401);
    expect(res.body.error).toBeTruthy();
  });
});

describe("POST /auth/refresh", () => {
  it("returns 401 when no refresh cookie present", async () => {
    const res = await request(app).post("/auth/refresh");
    expect(res.status).toBe(401);
    expect(res.body.error).toMatch(/Missing refresh token/i);
  });

  it("returns 401 for unknown token hash", async () => {
    pool.query.mockResolvedValueOnce({ rows: [] });
    const res = await request(app)
      .post("/auth/refresh")
      .set("Cookie", "refresh_token=unknowntoken");
    expect(res.status).toBe(401);
  });
});

describe("POST /auth/logout", () => {
  it("returns 401 without auth token", async () => {
    const res = await request(app).post("/auth/logout");
    expect(res.status).toBe(401);
  });
});

describe("Protected route without token", () => {
  it("GET /api/v1/alerts returns 401", async () => {
    const res = await request(app).get("/api/v1/alerts");
    expect(res.status).toBe(401);
  });

  it("GET /api/v1/settings returns 401", async () => {
    const res = await request(app).get("/api/v1/settings");
    expect(res.status).toBe(401);
  });
});
