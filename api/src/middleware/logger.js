/**
 * Structured JSON request logger middleware.
 */

export function logger(req, res, next) {
  const start = Date.now();
  res.on("finish", () => {
    console.log(
      JSON.stringify({
        level: "info",
        msg: "http.request",
        method: req.method,
        path: req.path,
        status: res.statusCode,
        ms: Date.now() - start,
      })
    );
  });
  next();
}
