"""Database configuration.

This module configures the SQLite database used by both the FastAPI
backend and the local MCP Ticket Server subprocess.
"""

from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.timeouts import (
    OPERATION_TIMEOUT_SECONDS,
    SQLITE_BUSY_TIMEOUT_MILLISECONDS,
)


APP_DIR = Path(__file__).resolve().parents[1]
DATABASE_PATH = APP_DIR / "mcp_ticket_analyzer.db"
DATABASE_URL = f"sqlite:///{DATABASE_PATH.as_posix()}"


class Base(DeclarativeBase):
    pass


engine = create_engine(
    DATABASE_URL,
    connect_args={
        "check_same_thread": False,
        "timeout": OPERATION_TIMEOUT_SECONDS,
    },
)


@event.listens_for(engine, "connect")
def configure_sqlite_connection(dbapi_connection, connection_record) -> None:
    """Enable WAL and apply the shared operation limit to lock waits."""

    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute(f"PRAGMA busy_timeout={SQLITE_BUSY_TIMEOUT_MILLISECONDS}")
    cursor.close()


SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def get_db() -> Generator[Session, None, None]:
    """Yield a database session and close it after use.

    This generator is intended to be used as a FastAPI dependency so
    that each request gets its own SQLAlchemy session that is cleaned up
    automatically.
    """

    with SessionLocal() as db:
        yield db
