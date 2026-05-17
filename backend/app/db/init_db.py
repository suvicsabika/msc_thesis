from app.db.database import Base, engine
from app.models.response_draft import ResponseDraftModel
from app.models.ticket import TicketModel


def create_db_and_tables() -> None:
    """Create database tables required by the application."""

    Base.metadata.create_all(bind=engine)