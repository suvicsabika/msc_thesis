import json
"""MCP Ticket Server implementation for local ticket analysis resources and tools.

This module defines resources and tools exposed to the host-side MCP client.
"""

from datetime import datetime, timezone
from typing import Literal

from mcp.server.fastmcp import FastMCP

from app.db.database import SessionLocal
from app.models.response_draft import ResponseDraftModel
from app.models.ticket import TicketModel


mcp = FastMCP("mcp-ticket-analyzer")


def get_ticket_or_raise(db, ticket_id: str) -> TicketModel:
    """Fetch a ticket from the database or raise a clear error when missing."""

    ticket = db.get(TicketModel, ticket_id)

    if ticket is None:
        raise ValueError(f"Ticket not found: {ticket_id}")

    return ticket


def serialize_ticket(ticket: TicketModel) -> dict:
    return {
        "id": ticket.id,
        "subject": ticket.subject,
        "body": ticket.body,
        "customer": ticket.customer,
        "customerEmail": ticket.customerEmail,
        "category": ticket.category,
        "priority": ticket.priority,
        "sentiment": ticket.sentiment,
        "sla": ticket.sla,
        "slaState": ticket.slaState,
        "status": ticket.status,
        "updatedAt": ticket.updatedAt,
        "owner": ticket.owner,
    }


@mcp.resource("tickets://index")
def tickets_index_resource() -> str:
    """Read the available ticket resource index as JSON."""

    with SessionLocal() as db:
        tickets = (
            db.query(TicketModel)
            .order_by(TicketModel.createdAt.desc())
            .all()
        )

        return json.dumps(
            {
                "tickets": [
                    {
                        "id": ticket.id,
                        "subject": ticket.subject,
                        "customer": ticket.customer,
                        "status": ticket.status,
                        "priority": ticket.priority,
                        "sentiment": ticket.sentiment,
                        "resources": {
                            "raw": f"ticket://{ticket.id}/raw",
                            "classification": f"ticket://{ticket.id}/classification",
                            "priority": f"ticket://{ticket.id}/priority",
                            "draftResponse": f"ticket://{ticket.id}/draft_response",
                            "history": f"ticket://{ticket.id}/history",
                        },
                    }
                    for ticket in tickets
                ]
            },
            indent=2,
            ensure_ascii=False,
        )


@mcp.resource("ticket://{ticket_id}/raw")
def ticket_raw_resource(ticket_id: str) -> str:
    """Read the raw ticket content and metadata as JSON."""

    with SessionLocal() as db:
        ticket = get_ticket_or_raise(db, ticket_id)

        return json.dumps(
            serialize_ticket(ticket),
            indent=2,
            ensure_ascii=False,
        )


@mcp.resource("ticket://{ticket_id}/classification")
def ticket_classification_resource(ticket_id: str) -> str:
    """Read the current classification-related ticket fields as JSON."""

    with SessionLocal() as db:
        ticket = get_ticket_or_raise(db, ticket_id)

        return json.dumps(
            {
                "ticketId": ticket.id,
                "category": ticket.category,
                "sentiment": ticket.sentiment,
                "priority": ticket.priority,
                "sla": ticket.sla,
                "slaState": ticket.slaState,
            },
            indent=2,
            ensure_ascii=False,
        )


@mcp.resource("ticket://{ticket_id}/priority")
def ticket_priority_resource(ticket_id: str) -> str:
    """Read the current priority and SLA status of a ticket as JSON."""

    with SessionLocal() as db:
        ticket = get_ticket_or_raise(db, ticket_id)

        return json.dumps(
            {
                "ticketId": ticket.id,
                "priority": ticket.priority,
                "sla": ticket.sla,
                "slaState": ticket.slaState,
                "status": ticket.status,
            },
            indent=2,
            ensure_ascii=False,
        )


@mcp.resource("ticket://{ticket_id}/draft_response")
def ticket_draft_response_resource(ticket_id: str) -> str:
    """Read the latest saved response draft for a ticket as JSON."""

    with SessionLocal() as db:
        ticket = get_ticket_or_raise(db, ticket_id)

        draft = (
            db.query(ResponseDraftModel)
            .filter(ResponseDraftModel.ticketId == ticket.id)
            .order_by(ResponseDraftModel.createdAt.desc())
            .first()
        )

        if draft is None:
            return json.dumps(
                {
                    "ticketId": ticket.id,
                    "draft": None,
                    "requiresApproval": True,
                    "reason": "No response draft has been saved for this ticket.",
                },
                indent=2,
                ensure_ascii=False,
            )

        return json.dumps(
            {
                "ticketId": ticket.id,
                "draft": draft.draft,
                "requiresApproval": draft.requiresApproval,
                "reason": draft.reason,
                "updatedAt": draft.updatedAt.isoformat(),
            },
            indent=2,
            ensure_ascii=False,
        )


@mcp.resource("ticket://{ticket_id}/history")
def ticket_history_resource(ticket_id: str) -> str:
    """Read a compact ticket history as JSON."""

    with SessionLocal() as db:
        ticket = get_ticket_or_raise(db, ticket_id)

        return json.dumps(
            {
                "ticketId": ticket.id,
                "summary": (
                    f"Ticket {ticket.id} is currently {ticket.status}. "
                    f"The latest update was {ticket.updatedAt}."
                ),
                "events": [
                    {
                        "type": "created",
                        "description": "Ticket was submitted by the customer.",
                    },
                    {
                        "type": "current_status",
                        "description": f"Current ticket status is {ticket.status}.",
                    },
                ],
            },
            indent=2,
            ensure_ascii=False,
        )


@mcp.tool()
def set_ticket_classification(
    ticket_id: str,
    category: Literal[
        "General",
        "Access",
        "Billing",
        "API",
        "Bug",
        "Feature Request",
        "Performance",
    ],
    confidence: float,
    reason: str,
) -> dict:
    """Set the classification category of a support ticket."""

    with SessionLocal() as db:
        ticket = get_ticket_or_raise(db, ticket_id)

        ticket.category = category
        ticket.updatedAt = "Just now"

        db.commit()
        db.refresh(ticket)

        return {
            "ticketId": ticket.id,
            "category": ticket.category,
            "confidence": confidence,
            "reason": reason,
        }


@mcp.tool()
def set_ticket_sentiment(
    ticket_id: str,
    sentiment: Literal["Negative", "Neutral", "Positive"],
    score: float,
    reason: str,
) -> dict:
    """Set the detected customer sentiment of a support ticket."""

    with SessionLocal() as db:
        ticket = get_ticket_or_raise(db, ticket_id)

        ticket.sentiment = sentiment
        ticket.updatedAt = "Just now"

        db.commit()
        db.refresh(ticket)

        return {
            "ticketId": ticket.id,
            "sentiment": ticket.sentiment,
            "score": score,
            "reason": reason,
        }


@mcp.tool()
def set_ticket_intent(
    ticket_id: str,
    intent: Literal[
        "Issue report",
        "Billing question",
        "How-to request",
        "Feature request",
        "General inquiry",
    ],
    confidence: float,
) -> dict:
    """Record the extracted customer intent for a support ticket."""

    with SessionLocal() as db:
        ticket = get_ticket_or_raise(db, ticket_id)

        return {
            "ticketId": ticket.id,
            "intent": intent,
            "confidence": confidence,
            "stored": False,
            "reason": "Customer intent is returned by the workflow but is not persisted in the ticket table yet.",
        }


@mcp.tool()
def set_ticket_priority(
    ticket_id: str,
    priority: Literal["Low", "Medium", "High", "Very High"],
    sla: str,
    sla_state: Literal["critical", "warning", "safe"],
    confidence: float,
    reason: str,
) -> dict:
    """Set the priority and SLA status of a support ticket."""

    with SessionLocal() as db:
        ticket = get_ticket_or_raise(db, ticket_id)

        ticket.priority = priority
        ticket.sla = sla
        ticket.slaState = sla_state
        ticket.updatedAt = "Just now"

        db.commit()
        db.refresh(ticket)

        return {
            "ticketId": ticket.id,
            "priority": ticket.priority,
            "sla": ticket.sla,
            "slaState": ticket.slaState,
            "confidence": confidence,
            "reason": reason,
        }


@mcp.tool()
def save_response_draft(
    ticket_id: str,
    draft: str,
    requires_approval: Literal[True],
    reason: str,
) -> dict:
    """Save a customer response draft for human review."""

    requires_approval = True

    with SessionLocal() as db:
        ticket = get_ticket_or_raise(db, ticket_id)

        response_draft = ResponseDraftModel(
            ticketId=ticket.id,
            draft=draft,
            requiresApproval=requires_approval,
            reason=reason,
            updatedAt=datetime.now(timezone.utc),
        )

        db.add(response_draft)
        db.commit()
        db.refresh(response_draft)

        return {
            "ticketId": ticket.id,
            "draftId": response_draft.id,
            "requiresApproval": response_draft.requiresApproval,
            "reason": response_draft.reason,
        }


@mcp.prompt()
def ticket_triage_prompt(ticket_id: str) -> str:
    """Create a reusable triage workflow prompt for a support ticket."""

    return (
        f"Analyze support ticket {ticket_id}. "
        f"First read ticket://{ticket_id}/raw. "
        f"Then decide the classification, sentiment, intent, priority, and response draft. "
        f"Use MCP tools to save the resulting ticket state. "
        f"The response draft must require human approval before it can be sent."
    )


@mcp.prompt()
def response_review_prompt(ticket_id: str) -> str:
    """Create a reusable prompt for reviewing a generated response draft."""

    return (
        f"Review the saved response draft for ticket {ticket_id}. "
        f"Check whether it is accurate, polite, concise, and safe to send to the customer."
    )


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()