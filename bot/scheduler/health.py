"""Minimal HTTP health-check server for the bot process."""

import json
from http.server import BaseHTTPRequestHandler, HTTPServer

from config import HEALTH_PORT
import structlog

log = structlog.get_logger()


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            body = json.dumps({"status": "ok", "service": "bot"}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, *args) -> None:  # silence default access log
        pass


def start_health_server() -> None:
    server = HTTPServer(("0.0.0.0", HEALTH_PORT), HealthHandler)
    log.info("health_server.started", port=HEALTH_PORT)
    server.serve_forever()
