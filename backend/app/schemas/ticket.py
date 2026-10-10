"""Request and response schemas for ticket endpoints."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.schemas.types import (
    TicketPriority,
    TicketSentiment,
    TicketSlaState,
    TicketStatus,
)


class TicketCreate(BaseModel):
    subject: str = Field(min_length=3, max_length=255)
    body: str = Field(min_length=10)
    customer: str = Field(min_length=2, max_length=120)
    customerEmail: EmailStr
    category: str = Field(default="General", max_length=80)


class TicketBulkCreate(BaseModel):
    """Create multiple tickets for testing when DEBUG is enabled."""

    # Require explicit opt-in before making paid analysis requests.
    analyze: bool = False
    tickets: list[TicketCreate] = Field(
        min_length=1,
        max_length=100,
    )


class TicketRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    subject: str
    body: str
    customer: str
    customerEmail: str
    category: str
    priority: TicketPriority
    sentiment: TicketSentiment
    sla: str
    slaState: TicketSlaState
    status: TicketStatus
    createdAt: datetime
    updatedAt: datetime
    owner: str


class TicketBulkCreateResult(BaseModel):
    """Result of a bulk ticket creation request."""

    createdCount: int
    analysisScheduled: bool
    tickets: list[TicketRead]
