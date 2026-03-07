/**
 * JWT authentication middleware.
 * Attaches decoded payload to req.user on success.
 */

import jwt from "jsonwebtoken";

const JWT_SECRET = process.env.JWT_SECRET ?? "dev-secret-change-in-prod";

export function requireAuth(req, res, next) {
  const header = req.headers.authorization ?? "";
  const token = header.startsWith("Bearer ") ? header.slice(7) : null;

  if (!token) {
    return res.status(401).json({ data: null, error: "Missing Bearer token", meta: {} });
  }

  try {
    req.user = jwt.verify(token, JWT_SECRET);
    next();
  } catch (err) {
    const message = err.name === "TokenExpiredError" ? "Token expired" : "Invalid token";
    return res.status(401).json({ data: null, error: message, meta: {} });
  }
}

/** Generate a signed token (used by /auth/login in dev/test). */
export function signToken(payload, expiresIn = "8h") {
  return jwt.sign(payload, JWT_SECRET, { expiresIn });
}
