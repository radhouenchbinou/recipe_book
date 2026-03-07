"""Database connection and session management."""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
import structlog

from config import DATABASE_URL

log = structlog.get_logger()

engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_size=5, max_overflow=10)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_session() -> Session:
    """Return a new database session. Caller is responsible for closing it."""
    return SessionLocal()


def healthcheck() -> bool:
    """Return True if the database is reachable."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        log.error("db.healthcheck.failed", error=str(exc))
        return False
