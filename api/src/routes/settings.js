/**
 * User settings routes.
 *
 * GET  /api/v1/settings  → fetch current user's notification preferences
 * PATCH /api/v1/settings → update current user's notification preferences
 */

import { Router } from "express";
import { z } from "zod";
import pool from "../services/db.js";

const router = Router();

const PatchSettingsSchema = z.object({
  notify_slack:  z.boolean().optional(),
  notify_email:  z.boolean().optional(),
  notify_sms:    z.boolean().optional(),
  slack_webhook: z.string().url().nullable().optional(),
  email_addr:    z.string().email().nullable().optional(),
  phone_number:  z.string().regex(/^\+[1-9]\d{6,14}$/).nullable().optional(),
  risk_tolerance: z.enum(["low", "medium", "high"]).optional(),
});

// ── GET /api/v1/settings ──────────────────────────────────────────────────
router.get("/", async (req, res, next) => {
  try {
    const userId = req.user.sub;
    const result = await pool.query(
      `SELECT notify_slack, notify_email, notify_sms,
              slack_webhook, email_addr, phone_number, risk_tolerance, updated_at
       FROM user_settings WHERE user_id = $1`,
      [userId]
    );

    if (!result.rows[0]) {
      // Auto-create defaults if missing
      await pool.query(
        `INSERT INTO user_settings (user_id) VALUES ($1) ON CONFLICT DO NOTHING`,
        [userId]
      );
      return res.json({
        data: { notify_slack: false, notify_email: false, notify_sms: false,
                slack_webhook: null, email_addr: null, phone_number: null,
                risk_tolerance: "medium" },
        error: null, meta: {},
      });
    }

    res.json({ data: result.rows[0], error: null, meta: {} });
  } catch (err) {
    next(err);
  }
});

// ── PATCH /api/v1/settings ────────────────────────────────────────────────
router.patch("/", async (req, res, next) => {
  try {
    const parse = PatchSettingsSchema.safeParse(req.body);
    if (!parse.success) {
      return res.status(400).json({ data: null, error: parse.error.errors[0].message, meta: {} });
    }

    const userId = req.user.sub;
    const updates = parse.data;

    // Build dynamic SET clause
    const fields = Object.keys(updates);
    if (fields.length === 0) {
      return res.status(400).json({ data: null, error: "No fields to update", meta: {} });
    }

    const setClauses = fields.map((f, i) => `${f} = $${i + 2}`).join(", ");
    const values = [userId, ...fields.map((f) => updates[f])];

    await pool.query(
      `INSERT INTO user_settings (user_id, ${fields.join(", ")}, updated_at)
       VALUES ($1, ${fields.map((_, i) => `$${i + 2}`).join(", ")}, NOW())
       ON CONFLICT (user_id) DO UPDATE SET ${setClauses}, updated_at = NOW()`,
      values
    );

    // Return updated row
    const result = await pool.query(
      `SELECT notify_slack, notify_email, notify_sms,
              slack_webhook, email_addr, phone_number, risk_tolerance, updated_at
       FROM user_settings WHERE user_id = $1`,
      [userId]
    );

    res.json({ data: result.rows[0], error: null, meta: {} });
  } catch (err) {
    next(err);
  }
});

export default router;
