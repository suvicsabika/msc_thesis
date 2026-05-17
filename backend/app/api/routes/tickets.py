import asyncio
import logging
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.ticket import TicketModel
from app.schemas.ticket import TicketCreate, TicketRead
from app.services.ticket_analysis_workflow import analyze_ticket_with_mcp_workflow
from app.models.response_draft import ResponseDraftModel
from app.schemas.response_draft import ResponseDraftRead


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tickets", tags=["tickets"])

ANALYSIS_TIMEOUT_SECONDS = 90


def create_ticket_id() -> str:
    """Create a short unique ticket identifier."""

    return f"MCP-{uuid4().hex[:8].upper()}"


async def run_ticket_analysis_job(ticket_id: str) -> None:
    """Run the MCP analysis workflow with a hard timeout."""

    logger.info("Background MCP analysis started | ticket_id=%s", ticket_id)

    try:
        await asyncio.wait_for(
            analyze_ticket_with_mcp_workflow(ticket_id),
            timeout=ANALYSIS_TIMEOUT_SECONDS,
        )

        logger.info("Background MCP analysis completed | ticket_id=%s", ticket_id)

    except asyncio.TimeoutError:
        logger.exception(
            "Background MCP analysis timed out | ticket_id=%s | timeout_seconds=%s",
            ticket_id,
            ANALYSIS_TIMEOUT_SECONDS,
        )

    except Exception:
        logger.exception("Background MCP analysis failed | ticket_id=%s", ticket_id)


def run_ticket_analysis_background(ticket_id: str) -> None:
    """Run ticket analysis in a worker thread.

    FastAPI BackgroundTasks executes normal functions in a threadpool.
    This wrapper prevents long-running AI/MCP work from blocking the main
    application event loop.
    """

    asyncio.run(run_ticket_analysis_job(ticket_id))


@router.get("", response_model=list[TicketRead])
def get_tickets(db: Session = Depends(get_db)):
    return (
        db.query(TicketModel)
        .order_by(TicketModel.createdAt.desc())
        .all()
    )


@router.post(
    "",
    response_model=TicketRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a support ticket",
    description="Creates a support ticket and starts automatic MCP-based analysis in the background.",
)
def create_ticket(
    payload: TicketCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    ticket = TicketModel(
        id=create_ticket_id(),
        subject=payload.subject,
        body=payload.body,
        customer=payload.customer,
        customerEmail=payload.customerEmail,
        category=payload.category,
        priority="Low",
        sentiment="Neutral",
        sla="1 day",
        slaState="safe",
        status="Open",
        updatedAt="Just now",
        owner="Unassigned",
    )

    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    background_tasks.add_task(run_ticket_analysis_background, ticket.id)

    return ticket


@router.post(
    "/{ticket_id}/analyze",
    summary="Analyze a ticket with MCP",
    description="Runs the MCP Host workflow manually for a selected ticket.",
)
async def analyze_ticket(ticket_id: str):
    return await asyncio.wait_for(
        analyze_ticket_with_mcp_workflow(ticket_id),
        timeout=ANALYSIS_TIMEOUT_SECONDS,
    )


@router.get(
    "/{ticket_id}",
    response_model=TicketRead,
    summary="Get ticket details",
    description="Returns the full stored support ticket data for the given ticket ID.",
)
def get_ticket(ticket_id: str, db: Session = Depends(get_db)):
    ticket = db.get(TicketModel, ticket_id)

    if ticket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found.",
        )

    return ticket


@router.get(
    "/{ticket_id}/draft",
    response_model=ResponseDraftRead | None,
    summary="Get latest response draft",
    description="Returns the latest saved AI-generated response draft for a ticket, if one exists.",
)
def get_latest_ticket_draft(ticket_id: str, db: Session = Depends(get_db)):
    ticket = db.get(TicketModel, ticket_id)

    if ticket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found.",
        )

    return (
        db.query(ResponseDraftModel)
        .filter(ResponseDraftModel.ticketId == ticket_id)
        .order_by(ResponseDraftModel.createdAt.desc())
        .first()
    )