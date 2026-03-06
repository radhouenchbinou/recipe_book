/**
 * Central error handler — always returns { data, error, meta } envelope.
 */

export function errorHandler(err, _req, res, _next) {
  const status = err.status ?? err.statusCode ?? 500;
  const message =
    process.env.NODE_ENV === "production" && status === 500
      ? "Internal server error"
      : err.message ?? "Unknown error";

  console.error(
    JSON.stringify({ level: "error", msg: "http.error", status, error: message, stack: err.stack })
  );

  res.status(status).json({ data: null, error: message, meta: {} });
}
