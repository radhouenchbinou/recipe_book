/**
 * Redis client — used for response caching.
 */

import Redis from "ioredis";

const redis = new Redis(process.env.REDIS_URL ?? "redis://localhost:6379", {
  lazyConnect: true,
  maxRetriesPerRequest: 2,
});

redis.on("error", (err) => {
  console.error(JSON.stringify({ level: "error", msg: "redis.error", error: err.message }));
});

/**
 * Get a cached value or compute + cache it.
 * @param {string} key
 * @param {number} ttlSeconds
 * @param {() => Promise<any>} fn
 */
export async function cached(key, ttlSeconds, fn) {
  try {
    const hit = await redis.get(key);
    if (hit) return JSON.parse(hit);
  } catch {
    // Cache miss on error — fall through to compute
  }

  const value = await fn();

  try {
    await redis.setex(key, ttlSeconds, JSON.stringify(value));
  } catch {
    // Best-effort cache write
  }

  return value;
}

export default redis;
