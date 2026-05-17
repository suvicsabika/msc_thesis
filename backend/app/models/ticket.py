from datetime import datetime, timezone

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class TicketModel(Base):
    __tablename__ = "tickets"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, index=True)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)

    customer: Mapped[str] = mapped_column(String(120), nullable=False)
    customerEmail: Mapped[str] = mapped_column(String(255), nullable=False)

    category: Mapped[str] = mapped_column(String(80), nullable=False, default="General")
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="Low")
    sentiment: Mapped[str] = mapped_column(String(20), nullable=False, default="Neutral")

    sla: Mapped[str] = mapped_column(String(40), nullable=False, default="1d")
    slaState: Mapped[str] = mapped_column(String(20), nullable=False, default="safe")

    status: Mapped[str] = mapped_column(String(40), nullable=False, default="Open")
    updatedAt: Mapped[str] = mapped_column(String(40), nullable=False, default="Just now")
    owner: Mapped[str] = mapped_column(String(80), nullable=False, default="Unassigned")

    createdAt: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )