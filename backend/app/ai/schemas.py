"""Structured schemas for AI ticket analysis results.

This module defines the Pydantic models used to validate the structured
responses returned by the OpenAI ticket triage process.
"""

from typing import Literal

from pydantic import BaseModel, Field


class TicketTriageDecision(BaseModel):
    """The structured triage decision produced by the AI model."""
    category: Literal[
        "General",
        "Access",
        "Billing",
        "API",
        "Bug",
        "Feature Request",
        "Performance",
    ]
    classificationConfidence: float = Field(ge=0.0, le=1.0)
    classificationReason: str

    sentiment: Literal["Negative", "Neutral", "Positive"]
    sentimentScore: float = Field(ge=0.0, le=1.0)
    sentimentReason: str

    customerIntent: Literal[
        "Issue report",
        "Billing question",
        "How-to request",
        "Feature request",
        "General inquiry",
    ]
    intentConfidence: float = Field(ge=0.0, le=1.0)

    priority: Literal["Low", "Medium", "High", "Very High"]
    slaState: Literal["critical", "warning", "safe"]
    sla: str
    priorityConfidence: float = Field(ge=0.0, le=1.0)
    priorityReason: str

    responseDraft: str
    requiresApproval: Literal[True]
    responseDraftReason: str

    reasoningSummary: str


class TicketAnalysisWorkflowResult(BaseModel):
    """Wraps the ticket analysis result and the corresponding MCP tool outputs."""

    ticketId: str
    decision: TicketTriageDecision
    mcpToolResults: list[dict]