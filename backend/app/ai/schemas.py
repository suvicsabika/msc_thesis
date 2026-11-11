"""Schemas for ticket analysis results."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.ticket_policy import validate_ticket_sla
from app.schemas.types import (
    TicketCategory,
    TicketPriority,
    TicketSentiment,
    TicketSla,
)


class TicketTriageDecision(BaseModel):
    """The structured triage decision produced by the AI model."""

    model_config = ConfigDict(extra="forbid")

    category: TicketCategory
    classificationConfidence: float = Field(ge=0.0, le=1.0)
    classificationReason: str

    sentiment: TicketSentiment
    sentimentScore: float = Field(ge=0.0, le=1.0)
    sentimentReason: str

    priority: TicketPriority
    sla: TicketSla
    priorityConfidence: float = Field(ge=0.0, le=1.0)
    priorityReason: str

    responseDraft: str
    requiresApproval: Literal[True]
    responseDraftReason: str

    reasoningSummary: str

    @model_validator(mode="after")
    def check_priority_sla(self):
        validate_ticket_sla(self.priority, self.sla)
        return self


class TicketTokenUsage(BaseModel):
    """Provider-reported tokens summed across one analysis workflow."""

    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    total_tokens: int = Field(ge=0)


class TicketAnalysisWorkflowResult(BaseModel):
    """Ticket analysis result and corresponding MCP tool outputs."""

    ticketId: str
    decision: TicketTriageDecision
    mcpToolResults: list[dict]
    mcpResourceReads: list[str] = Field(default_factory=list)
    usage: TicketTokenUsage | None = None
    transport: Literal["mcp", "direct"] = "mcp"
