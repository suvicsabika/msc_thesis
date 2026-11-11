"""Ticket reads and writes shared by direct calls and the MCP server."""

import json
from datetime import datetime, timezone
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.ticket_policy import validate_ticket_sla
from app.db.database import SessionLocal
from app.models.response_draft import ResponseDraftModel
from app.models.ticket import TicketModel
from app.schemas.types import (
    TicketCategory,
    TicketPriority,
    TicketSentiment,
    TicketSla,
)


def get_ticket_or_raise(db: Session, ticket_id: str) -> TicketModel:
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
        "status": ticket.status,
        "updatedAt": ticket.updatedAt.isoformat(),
        "owner": ticket.owner,
    }


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


def ticket_raw_resource(ticket_id: str) -> str:
    """Read the raw ticket content and metadata as JSON."""

    with SessionLocal() as db:
        ticket = get_ticket_or_raise(db, ticket_id)

        return json.dumps(
            serialize_ticket(ticket),
            indent=2,
            ensure_ascii=False,
        )


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
            },
            indent=2,
            ensure_ascii=False,
        )


def ticket_priority_resource(ticket_id: str) -> str:
    """Read the current priority and SLA status of a ticket as JSON."""

    with SessionLocal() as db:
        ticket = get_ticket_or_raise(db, ticket_id)

        return json.dumps(
            {
                "ticketId": ticket.id,
                "priority": ticket.priority,
                "sla": ticket.sla,
                "status": ticket.status,
            },
            indent=2,
            ensure_ascii=False,
        )


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


def ticket_history_resource(ticket_id: str) -> str:
    """Read a compact ticket history as JSON."""

    with SessionLocal() as db:
        ticket = get_ticket_or_raise(db, ticket_id)

        return json.dumps(
            {
                "ticketId": ticket.id,
                "summary": (
                    f"Ticket {ticket.id} is currently {ticket.status}. "
                    f"The latest update was {ticket.updatedAt.isoformat()}."
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


def set_ticket_classification(
    ticket_id: str,
    category: TicketCategory,
    confidence: float,
    reason: str,
) -> dict:
    """Save the analyzed ticket category to the database."""

    with SessionLocal() as db:
        ticket = get_ticket_or_raise(db, ticket_id)

        ticket.category = category
        ticket.updatedAt = datetime.now(timezone.utc)

        db.commit()
        db.refresh(ticket)

        return {
            "ticketId": ticket.id,
            "category": ticket.category,
            "confidence": confidence,
            "reason": reason,
        }


def set_ticket_sentiment(
    ticket_id: str,
    sentiment: TicketSentiment,
    score: float,
    reason: str,
) -> dict:
    """Save the analyzed customer sentiment to the ticket database."""

    with SessionLocal() as db:
        ticket = get_ticket_or_raise(db, ticket_id)

        ticket.sentiment = sentiment
        ticket.updatedAt = datetime.now(timezone.utc)

        db.commit()
        db.refresh(ticket)

        return {
            "ticketId": ticket.id,
            "sentiment": ticket.sentiment,
            "score": score,
            "reason": reason,
        }


def set_ticket_priority(
    ticket_id: str,
    priority: TicketPriority,
    sla: TicketSla,
    confidence: float,
    reason: str,
) -> dict:
    """Save the analyzed priority and SLA label."""

    sla = validate_ticket_sla(priority, sla)

    with SessionLocal() as db:
        ticket = get_ticket_or_raise(db, ticket_id)

        ticket.priority = priority
        ticket.sla = sla
        ticket.updatedAt = datetime.now(timezone.utc)

        db.commit()
        db.refresh(ticket)

        return {
            "ticketId": ticket.id,
            "priority": ticket.priority,
            "sla": ticket.sla,
            "confidence": confidence,
            "reason": reason,
        }


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
