/**
 * PostgreSQL connection pool — shared across all route handlers.
 */

import pg from "pg";

const pool = new pg.Pool({
  connectionString: process.env.DATABASE_URL,
  max: 10,
  idleTimeoutMillis: 30_000,
  connectionTimeoutMillis: 5_000,
});

pool.on("error", (err) => {
  console.error(JSON.stringify({ level: "error", msg: "db.pool_error", error: err.message }));
});

export default pool;
