/**
 * Settings endpoint tests — GET/PATCH /api/v1/settings
 */

import { describe, it, expect, jest } from "@jest/globals";
import request from "supertest";
import app from "../src/app.js";
import jwt from "jsonwebtoken";

jest.mock("../src/services/db.js", () => ({
  default: { query: jest.fn() },
}));

import pool from "../src/services/db.js";

process.env.JWT_SECRET = "test-secret";
process.env.NODE_ENV = "test";

function makeToken(role = "trader") {
  return jwt.sign({ sub: 1, username: "alice", role }, "test-secret", { expiresIn: "1h" });
}

const MOCK_SETTINGS = {
  notify_slack: false,
  notify_email: false,
  notify_sms: false,
  slack_webhook: null,
  email_addr: null,
  phone_number: null,
  risk_tolerance: "medium",
  updated_at: new Date().toISOString(),
};

describe("GET /api/v1/settings", () => {
  it("returns 401 without token", async () => {
    const res = await request(app).get("/api/v1/settings");
    expect(res.status).toBe(401);
  });

  it("returns 200 with settings for authenticated user", async () => {
    pool.query.mockResolvedValueOnce({ rows: [MOCK_SETTINGS] });

    const res = await request(app)
      .get("/api/v1/settings")
      .set("Authorization", `Bearer ${makeToken()}`);

    expect(res.status).toBe(200);
    expect(res.body.data).toMatchObject({ risk_tolerance: "medium" });
    expect(res.body.error).toBeNull();
  });
});

describe("PATCH /api/v1/settings", () => {
  it("returns 401 without token", async () => {
    const res = await request(app).patch("/api/v1/settings").send({ risk_tolerance: "high" });
    expect(res.status).toBe(401);
  });

  it("returns 400 for invalid risk_tolerance", async () => {
    const res = await request(app)
      .patch("/api/v1/settings")
      .set("Authorization", `Bearer ${makeToken()}`)
      .send({ risk_tolerance: "extreme" });
    expect(res.status).toBe(400);
  });

  it("returns 400 for invalid email", async () => {
    const res = await request(app)
      .patch("/api/v1/settings")
      .set("Authorization", `Bearer ${makeToken()}`)
      .send({ email_addr: "not-an-email" });
    expect(res.status).toBe(400);
  });

  it("returns 400 for empty body", async () => {
    const res = await request(app)
      .patch("/api/v1/settings")
      .set("Authorization", `Bearer ${makeToken()}`)
      .send({});
    expect(res.status).toBe(400);
  });

  it("returns 200 for valid update", async () => {
    pool.query.mockResolvedValue({ rows: [{ ...MOCK_SETTINGS, risk_tolerance: "high" }] });

    const res = await request(app)
      .patch("/api/v1/settings")
      .set("Authorization", `Bearer ${makeToken()}`)
      .send({ risk_tolerance: "high" });

    expect(res.status).toBe(200);
    expect(res.body.data.risk_tolerance).toBe("high");
  });
});
