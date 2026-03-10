/**
 * JWT authentication + RBAC middleware.
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

/**
 * Role-based access control.
 * Usage: router.delete("/:id", requireAuth, authorize("admin", "trader"), handler)
 */
export function authorize(...roles) {
  return (req, res, next) => {
    if (!req.user || !roles.includes(req.user.role)) {
      return res.status(403).json({ data: null, error: "Insufficient permissions", meta: {} });
    }
    next();
  };
}

/** Generate a signed JWT. Default lifetime: 15 minutes. */
export function signToken(payload, expiresIn = "15m") {
  return jwt.sign(payload, JWT_SECRET, { expiresIn });
}
