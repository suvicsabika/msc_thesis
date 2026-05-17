from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class ResponseDraftModel(Base):
    __tablename__ = "response_drafts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ticketId: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("tickets.id"),
        index=True,
        nullable=False,
    )
    draft: Mapped[str] = mapped_column(Text, nullable=False)
    requiresApproval: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)

    createdAt: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updatedAt: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )