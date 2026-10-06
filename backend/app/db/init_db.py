"""Register ORM models and create their database tables."""

from app.db.database import Base, engine

# Importing models registers their tables with Base.metadata.
from app.models import response_draft, ticket  # noqa: F401


def create_db_and_tables() -> None:
    """Create database tables required by the application."""

    Base.metadata.create_all(bind=engine)
