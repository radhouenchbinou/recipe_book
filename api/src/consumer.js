/**
 * RabbitMQ consumer — subscribes to trading.events topic exchange
 * and relays messages to the appropriate Socket.io room.
 *
 * Routing key → room → Socket.io event mapping:
 *   rec.new       → recs    → newRecommendation
 *   analysis.done → market  → scoresUpdated
 *   alert.trigger → alerts  → alertTriggered
 */

import amqplib from "amqplib";
import { io } from "./app.js";

const EXCHANGE = "trading.events";
const BINDINGS = {
  "rec.new":       { room: "recs",    event: "newRecommendation" },
  "analysis.done": { room: "market",  event: "scoresUpdated" },
  "alert.trigger": { room: "alerts",  event: "alertTriggered" },
};

export async function startConsumer() {
  const url = process.env.RABBITMQ_URL ?? "amqp://trader:trader@localhost:5672";
  const conn = await amqplib.connect(url);
  const ch   = await conn.createChannel();

  await ch.assertExchange(EXCHANGE, "topic", { durable: true });

  for (const [routingKey, { room, event }] of Object.entries(BINDINGS)) {
    const q = await ch.assertQueue("", { exclusive: true });
    await ch.bindQueue(q.queue, EXCHANGE, routingKey);

    ch.consume(q.queue, (msg) => {
      if (!msg) return;
      try {
        const payload = JSON.parse(msg.content.toString());
        io.to(room).emit(event, payload);
      } catch {
        // Ignore malformed messages
      }
      ch.ack(msg);
    });
  }

  conn.on("error", (err) => {
    console.log(JSON.stringify({ level: "error", msg: "rabbitmq.connection.error", error: err.message }));
  });
}
