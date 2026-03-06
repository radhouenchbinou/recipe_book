/**
 * POST /auth/login — issues a JWT for dev/test use.
 * In production replace with your SSO / OAuth provider.
 */

import { Router } from "express";
import { z } from "zod";
import { signToken } from "../middleware/auth.js";

const router = Router();

const LoginSchema = z.object({
  username: z.string().min(1),
  password: z.string().min(1),
});

// Single hardcoded dev user — replace with DB lookup in production
const DEV_USER = {
  username: process.env.DEV_USERNAME ?? "admin",
  password: process.env.DEV_PASSWORD ?? "changeme",
};

router.post("/login", (req, res) => {
  const parse = LoginSchema.safeParse(req.body);
  if (!parse.success) {
    return res.status(400).json({ data: null, error: "username and password required", meta: {} });
  }

  const { username, password } = parse.data;
  if (username !== DEV_USER.username || password !== DEV_USER.password) {
    return res.status(401).json({ data: null, error: "Invalid credentials", meta: {} });
  }

  const token = signToken({ sub: username, role: "trader" });
  res.json({ data: { token }, error: null, meta: {} });
});

export default router;
