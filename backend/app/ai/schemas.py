"""Structured schemas for AI ticket analysis results.

This module defines the Pydantic models used to validate the structured
responses returned by the OpenAI ticket triage process.
"""

from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.types import (
    TicketCategory,
    TicketIntent,
    TicketPriority,
    TicketSentiment,
    TicketSlaState,
)


class TicketTriageDecision(BaseModel):
    """The structured triage decision produced by the AI model."""

    category: TicketCategory
    classificationConfidence: float = Field(ge=0.0, le=1.0)
    classificationReason: str

    sentiment: TicketSentiment
    sentimentScore: float = Field(ge=0.0, le=1.0)
    sentimentReason: str

    customerIntent: TicketIntent
    intentConfidence: float = Field(ge=0.0, le=1.0)

    priority: TicketPriority
    slaState: TicketSlaState
    sla: str
    priorityConfidence: float = Field(ge=0.0, le=1.0)
    priorityReason: str

    responseDraft: str
    requiresApproval: Literal[True]
    responseDraftReason: str

    reasoningSummary: str


class TicketAnalysisWorkflowResult(BaseModel):
    """Ticket analysis result and corresponding MCP tool outputs."""

    ticketId: str
    decision: TicketTriageDecision
    mcpToolResults: list[dict]
