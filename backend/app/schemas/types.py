"""Ticket values shared by REST schemas, AI decisions, and MCP tools."""

from typing import Literal


TicketCategory = Literal[
    "General",
    "Access",
    "Billing",
    "API",
    "Bug",
    "Feature Request",
    "Performance",
]
TicketSentiment = Literal["Negative", "Neutral", "Positive"]
TicketPriority = Literal["Low", "Medium", "High", "Very High"]
TicketSlaState = Literal["critical", "warning", "safe"]
TicketStatus = Literal["Open", "In Progress", "Resolved"]
TicketIntent = Literal[
    "Issue report",
    "Billing question",
    "How-to request",
    "Feature request",
    "General inquiry",
]
