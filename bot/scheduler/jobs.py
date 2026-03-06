"""APScheduler job definitions."""

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
import structlog

from config import MARKET_DATA_CRON, NEWS_FETCH_CRON, ANALYSIS_CRON

log = structlog.get_logger()


def job_fetch_market_data() -> None:
    from collectors.market_data import fetch_all_symbols
    log.info("job.market_data.start")
    fetch_all_symbols()
    log.info("job.market_data.done")


def job_fetch_news() -> None:
    from collectors.news_fetcher import fetch_news
    log.info("job.news.start")
    fetch_news()
    log.info("job.news.done")


def job_run_analysis() -> None:
    from analysis.pipeline import run_analysis_pipeline
    log.info("job.analysis.start")
    run_analysis_pipeline()
    log.info("job.analysis.done")


def build_scheduler() -> BlockingScheduler:
    scheduler = BlockingScheduler(timezone="America/New_York")

    scheduler.add_job(
        job_fetch_market_data,
        CronTrigger.from_crontab(MARKET_DATA_CRON),
        id="market_data",
        name="Fetch daily market data",
        misfire_grace_time=300,
    )
    scheduler.add_job(
        job_fetch_news,
        CronTrigger.from_crontab(NEWS_FETCH_CRON),
        id="news",
        name="Fetch news feed",
        misfire_grace_time=60,
    )
    scheduler.add_job(
        job_run_analysis,
        CronTrigger.from_crontab(ANALYSIS_CRON),
        id="analysis",
        name="Run analysis pipeline",
        misfire_grace_time=300,
    )

    return scheduler
