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
TicketSla = Literal["1 day", "12h", "4h", "1h"]
TicketStatus = Literal["Open", "In Progress", "Resolved"]
