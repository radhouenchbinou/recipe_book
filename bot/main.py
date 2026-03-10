"""Trading bot entry point — starts the scheduler and health server."""

import threading
import structlog

from scheduler.jobs import build_scheduler
from scheduler.health import start_health_server

log = structlog.get_logger()


def main() -> None:
    log.info("trading_bot.starting")

    # Health endpoint (simple HTTP server on HEALTH_PORT)
    health_thread = threading.Thread(target=start_health_server, daemon=True)
    health_thread.start()

    # APScheduler
    scheduler = build_scheduler()
    scheduler.start()
    log.info("trading_bot.scheduler_started", jobs=len(scheduler.get_jobs()))

    try:
        # Keep alive
        import time
        while True:
            time.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        log.info("trading_bot.stopping")
        scheduler.shutdown()


if __name__ == "__main__":
    main()
