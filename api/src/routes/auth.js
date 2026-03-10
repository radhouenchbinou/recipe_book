/**
 * Auth routes — multi-user, bcrypt passwords, refresh token rotation.
 *
 * POST /auth/register  → create account, return access JWT
 * POST /auth/login     → verify password, return access JWT + set refresh cookie
 * POST /auth/refresh   → rotate refresh token, return new access JWT
 * POST /auth/logout    → delete refresh token from DB, clear cookie
 */

import { Router } from "express";
import { createHash, randomBytes } from "crypto";
import bcrypt from "bcryptjs";
import { z } from "zod";
import pool from "../services/db.js";
import { signToken, requireAuth } from "../middleware/auth.js";

const router = Router();

const REFRESH_TTL_DAYS = 30;
const COOKIE_OPTS = {
  httpOnly: true,
  secure: process.env.NODE_ENV === "production",
  sameSite: "strict",
  maxAge: REFRESH_TTL_DAYS * 24 * 60 * 60 * 1000,
  path: "/auth/refresh",
};

const RegisterSchema = z.object({
  username: z.string().min(3).max(64),
  email: z.string().email(),
  password: z.string().min(8),
});

const LoginSchema = z.object({
  username: z.string().min(1),
  password: z.string().min(1),
});

function hashToken(raw) {
  return createHash("sha256").update(raw).digest("hex");
}

async function issueRefreshToken(userId, res) {
  const raw = randomBytes(48).toString("hex");
  const expiresAt = new Date(Date.now() + REFRESH_TTL_DAYS * 86400_000);

  await pool.query(
    `INSERT INTO refresh_tokens (user_id, token_hash, expires_at)
     VALUES ($1, $2, $3)`,
    [userId, hashToken(raw), expiresAt]
  );

  res.cookie("refresh_token", raw, COOKIE_OPTS);
}

// ── POST /auth/register ──────────────────────────────────────────────────────
router.post("/register", async (req, res, next) => {
  try {
    const parse = RegisterSchema.safeParse(req.body);
    if (!parse.success) {
      return res.status(400).json({ data: null, error: parse.error.errors[0].message, meta: {} });
    }

    const { username, email, password } = parse.data;
    const passwordHash = await bcrypt.hash(password, 12);

    let user;
    try {
      const result = await pool.query(
        `INSERT INTO users (username, email, password_hash)
         VALUES ($1, $2, $3)
         RETURNING id, username, email, role`,
        [username, email, passwordHash]
      );
      user = result.rows[0];
    } catch (err) {
      if (err.code === "23505") {
        return res.status(400).json({ data: null, error: "Username or email already taken", meta: {} });
      }
      throw err;
    }

    // Seed default user_settings row
    await pool.query(
      `INSERT INTO user_settings (user_id) VALUES ($1) ON CONFLICT DO NOTHING`,
      [user.id]
    );

    const token = signToken({ sub: user.id, username: user.username, role: user.role }, "15m");
    await issueRefreshToken(user.id, res);

    res.status(201).json({
      data: { token, user: { id: user.id, username: user.username, email: user.email, role: user.role } },
      error: null,
      meta: {},
    });
  } catch (err) {
    next(err);
  }
});

// ── POST /auth/login ─────────────────────────────────────────────────────────
router.post("/login", async (req, res, next) => {
  try {
    const parse = LoginSchema.safeParse(req.body);
    if (!parse.success) {
      return res.status(400).json({ data: null, error: "username and password required", meta: {} });
    }

    const { username, password } = parse.data;
    const result = await pool.query(
      `SELECT id, username, email, role, password_hash FROM users WHERE username = $1`,
      [username]
    );

    const user = result.rows[0];
    if (!user || !(await bcrypt.compare(password, user.password_hash))) {
      return res.status(401).json({ data: null, error: "Invalid credentials", meta: {} });
    }

    const token = signToken({ sub: user.id, username: user.username, role: user.role }, "15m");
    await issueRefreshToken(user.id, res);

    res.json({
      data: { token, user: { id: user.id, username: user.username, email: user.email, role: user.role } },
      error: null,
      meta: {},
    });
  } catch (err) {
    next(err);
  }
});

// ── POST /auth/refresh ───────────────────────────────────────────────────────
router.post("/refresh", async (req, res, next) => {
  try {
    const raw = req.cookies?.refresh_token;
    if (!raw) {
      return res.status(401).json({ data: null, error: "Missing refresh token", meta: {} });
    }

    const tokenHash = hashToken(raw);
    const result = await pool.query(
      `SELECT rt.id, rt.user_id, rt.expires_at, u.username, u.role
       FROM refresh_tokens rt
       JOIN users u ON u.id = rt.user_id
       WHERE rt.token_hash = $1`,
      [tokenHash]
    );

    const row = result.rows[0];
    if (!row) {
      return res.status(401).json({ data: null, error: "Invalid refresh token", meta: {} });
    }
    if (new Date(row.expires_at) < new Date()) {
      await pool.query(`DELETE FROM refresh_tokens WHERE id = $1`, [row.id]);
      return res.status(401).json({ data: null, error: "Refresh token expired", meta: {} });
    }

    // Token rotation: delete old, issue new
    await pool.query(`DELETE FROM refresh_tokens WHERE id = $1`, [row.id]);
    const token = signToken({ sub: row.user_id, username: row.username, role: row.role }, "15m");
    await issueRefreshToken(row.user_id, res);

    res.json({ data: { token }, error: null, meta: {} });
  } catch (err) {
    next(err);
  }
});

// ── POST /auth/logout ────────────────────────────────────────────────────────
router.post("/logout", requireAuth, async (req, res, next) => {
  try {
    const raw = req.cookies?.refresh_token;
    if (raw) {
      await pool.query(
        `DELETE FROM refresh_tokens WHERE token_hash = $1`,
        [hashToken(raw)]
      );
    }
    res.clearCookie("refresh_token", { path: "/auth/refresh" });
    res.json({ data: { ok: true }, error: null, meta: {} });
  } catch (err) {
    next(err);
  }
});

export default router;
