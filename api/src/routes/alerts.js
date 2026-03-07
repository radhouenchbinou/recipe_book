/**
 * GET    /api/v1/alerts         — list all active alerts
 * POST   /api/v1/alerts         — create an alert
 * DELETE /api/v1/alerts/:id     — delete an alert
 * PATCH  /api/v1/alerts/:id     — toggle active/inactive
 *
 * Task S4-T1-004
 */

import { Router } from "express";
import { z } from "zod";
import { requireAuth } from "../middleware/auth.js";
import pool from "../services/db.js";

const router = Router();
router.use(requireAuth);

const ALERT_TYPES = ["price_above", "price_below", "score_above", "score_below", "recommendation"];

const CreateSchema = z.object({
  symbol:     z.string().min(1).max(10),
  alert_type: z.enum(ALERT_TYPES),
  threshold:  z.number().optional(),
  message:    z.string().max(255).optional(),
});

/** GET /api/v1/alerts */
router.get("/", async (req, res, next) => {
  try {
    const rows = await pool.query(
      `SELECT a.id, s.ticker, a.alert_type, a.threshold, a.message,
              a.active, a.triggered_at, a.created_at
       FROM   alerts a
       JOIN   symbols s ON s.id = a.symbol_id
       ORDER  BY a.created_at DESC`
    );
    res.json({ data: rows.rows, error: null, meta: { count: rows.rowCount } });
  } catch (err) {
    next(err);
  }
});

/** POST /api/v1/alerts */
router.post("/", async (req, res, next) => {
  const parse = CreateSchema.safeParse(req.body);
  if (!parse.success) {
    return res.status(400).json({ data: null, error: parse.error.message, meta: {} });
  }

  const { symbol, alert_type, threshold, message } = parse.data;
  try {
    const row = await pool.query(
      `INSERT INTO alerts (symbol_id, alert_type, threshold, message)
       SELECT s.id, $2, $3, $4 FROM symbols s WHERE s.ticker = $1
       RETURNING id, alert_type, threshold, message, active, created_at`,
      [symbol.toUpperCase(), alert_type, threshold ?? null, message ?? null]
    );

    if (!row.rowCount) {
      return res.status(404).json({ data: null, error: `Symbol ${symbol} not found`, meta: {} });
    }

    res.status(201).json({ data: row.rows[0], error: null, meta: {} });
  } catch (err) {
    next(err);
  }
});

/** DELETE /api/v1/alerts/:id */
router.delete("/:id", async (req, res, next) => {
  try {
    const result = await pool.query(
      "DELETE FROM alerts WHERE id = $1::uuid RETURNING id",
      [req.params.id]
    );
    if (!result.rowCount) {
      return res.status(404).json({ data: null, error: "Alert not found", meta: {} });
    }
    res.json({ data: { deleted: req.params.id }, error: null, meta: {} });
  } catch (err) {
    next(err);
  }
});

/** PATCH /api/v1/alerts/:id — toggle { active: true|false } */
router.patch("/:id", async (req, res, next) => {
  const schema = z.object({ active: z.boolean() });
  const parse = schema.safeParse(req.body);
  if (!parse.success) {
    return res.status(400).json({ data: null, error: "Body must be { active: boolean }", meta: {} });
  }

  try {
    const result = await pool.query(
      "UPDATE alerts SET active = $1 WHERE id = $2::uuid RETURNING id, active",
      [parse.data.active, req.params.id]
    );
    if (!result.rowCount) {
      return res.status(404).json({ data: null, error: "Alert not found", meta: {} });
    }
    res.json({ data: result.rows[0], error: null, meta: {} });
  } catch (err) {
    next(err);
  }
});

export default router;
