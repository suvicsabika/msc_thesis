"""Schemas exposed by the Ticket MCP Server."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


TicketCategory = Literal[
    "General",
    "Access",
    "Billing",
    "API",
    "Bug",
    "Feature Request",
    "Performance",
]

TicketSentiment = Literal[
    "Negative",
    "Neutral",
    "Positive",
]

TicketPriority = Literal[
    "Low",
    "Medium",
    "High",
    "Very High",
]

TicketSlaState = Literal[
    "critical",
    "warning",
    "safe",
]


class TicketSnapshot(BaseModel):
    """Original customer-submitted ticket data."""

    model_config = ConfigDict(frozen=True)

    id: str
    subject: str
    body: str
    customer: str
    customerEmail: str
    createdAt: datetime


class TicketAnalysisUpdate(BaseModel):
    """Persistable fields of a completed ticket analysis."""

    category: TicketCategory
    sentiment: TicketSentiment
    priority: TicketPriority
    sla: str = Field(min_length=1, max_length=40)
    slaState: TicketSlaState

    responseDraft: str = Field(min_length=1)
    requiresApproval: Literal[True]
    responseDraftReason: str = Field(min_length=1)


class AppliedTicketAnalysis(BaseModel):
    """Structured confirmation returned after applying an analysis."""

    ticketId: str
    category: TicketCategory
    sentiment: TicketSentiment
    priority: TicketPriority
    sla: str
    slaState: TicketSlaState

    draftId: int
    requiresApproval: Literal[True]