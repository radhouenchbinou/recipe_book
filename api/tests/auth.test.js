/**
 * Auth endpoint tests — POST /auth/login
 */

import { describe, it, expect, beforeAll } from "@jest/globals";
import request from "supertest";
import app from "../src/app.js";

process.env.DATABASE_URL = "postgresql://trader:trader@localhost:5432/tradingbot_test";
process.env.DEV_USERNAME = "testuser";
process.env.DEV_PASSWORD = "testpass";

describe("POST /auth/login", () => {
  it("returns 200 and a token for valid credentials", async () => {
    const res = await request(app)
      .post("/auth/login")
      .send({ username: "testuser", password: "testpass" });

    expect(res.status).toBe(200);
    expect(res.body.data).toHaveProperty("token");
    expect(typeof res.body.data.token).toBe("string");
    expect(res.body.error).toBeNull();
  });

  it("returns 401 for wrong password", async () => {
    const res = await request(app)
      .post("/auth/login")
      .send({ username: "testuser", password: "wrong" });

    expect(res.status).toBe(401);
    expect(res.body.error).toBeTruthy();
  });

  it("returns 400 for missing fields", async () => {
    const res = await request(app).post("/auth/login").send({});
    expect(res.status).toBe(400);
  });

  it("returns 401 accessing protected route without token", async () => {
    const res = await request(app).get("/api/v1/alerts");
    expect(res.status).toBe(401);
  });
});
