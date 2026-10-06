"""MCP server exposing local ticket resources, tools, and prompts.

This module defines resources and tools exposed to the host-side MCP
client.
"""

import json
from datetime import datetime, timezone
from typing import Literal

from mcp.server import MCPServer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.models.response_draft import ResponseDraftModel
from app.models.ticket import TicketModel
from app.schemas.types import (
    TicketCategory,
    TicketIntent,
    TicketPriority,
    TicketSentiment,
    TicketSlaState,
)


mcp = MCPServer("mcp-ticket-analyzer", version="2.2.0")


def get_ticket_or_raise(db: Session, ticket_id: str) -> TicketModel:
    """Fetch a ticket from the database or raise a clear error when
    missing.
    """

    ticket = db.get(TicketModel, ticket_id)

    if ticket is None:
        raise ValueError(f"Ticket not found: {ticket_id}")

    return ticket


def serialize_ticket(ticket: TicketModel) -> dict:
    """Serialize stored fields without REST response validation."""

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
        statement = select(TicketModel).order_by(TicketModel.createdAt.desc())
        tickets = db.scalars(statement).all()

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
                            "classification": (
                                f"ticket://{ticket.id}/classification"
                            ),
                            "priority": f"ticket://{ticket.id}/priority",
                            "draftResponse": (
                                f"ticket://{ticket.id}/draft_response"
                            ),
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

        statement = (
            select(ResponseDraftModel)
            .where(ResponseDraftModel.ticketId == ticket.id)
            .order_by(ResponseDraftModel.createdAt.desc())
            .limit(1)
        )
        draft = db.scalar(statement)

        if draft is None:
            return json.dumps(
                {
                    "ticketId": ticket.id,
                    "draft": None,
                    "requiresApproval": True,
                    "reason": (
                        "No response draft has been saved for this ticket."
                    ),
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
                        "description": (
                            f"Current ticket status is {ticket.status}."
                        ),
                    },
                ],
            },
            indent=2,
            ensure_ascii=False,
        )


@mcp.tool()
def set_ticket_classification(
    ticket_id: str,
    category: TicketCategory,
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
    sentiment: TicketSentiment,
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
    intent: TicketIntent,
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
            "reason": (
                "Customer intent is returned by the workflow but is not "
                "persisted in the ticket table yet."
            ),
        }


@mcp.tool()
def set_ticket_priority(
    ticket_id: str,
    priority: TicketPriority,
    sla: str,
    sla_state: TicketSlaState,
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
        "Then decide the classification, sentiment, intent, priority, "
        "and response draft. "
        "Use MCP tools to save the resulting ticket state. "
        "The response draft must require human approval before it can be sent."
    )


@mcp.prompt()
def response_review_prompt(ticket_id: str) -> str:
    """Create a reusable prompt for reviewing a generated response
    draft.
    """

    return (
        f"Review the saved response draft for ticket {ticket_id}. "
        "Check whether it is accurate, polite, concise, "
        "and safe to send to the customer."
    )


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
