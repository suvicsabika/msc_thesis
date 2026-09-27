"""REST endpoints for support ticket creation and analysis."""

import asyncio
import logging
import os
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.schemas import TicketAnalysisWorkflowResult
from app.db.database import get_db
from app.models.response_draft import ResponseDraftModel
from app.models.ticket import TicketModel
from app.schemas.response_draft import ResponseDraftRead
from app.schemas.ticket import (
    TicketBulkCreate,
    TicketBulkCreateResult,
    TicketCreate,
    TicketRead,
)
from app.services.ticket_analysis_workflow import analyze_ticket_with_mcp_workflow

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tickets", tags=["tickets"])

ANALYSIS_TIMEOUT_SECONDS = 90
BULK_ANALYSIS_CONCURRENCY = 3


def require_debug_mode() -> None:
    """Allow bulk operations only when DEBUG is explicitly true."""

    if os.getenv("DEBUG", "False").strip().lower() != "true":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bulk ticket operations require DEBUG=True.",
        )


def create_ticket_id() -> str:
    """Create a short unique ticket identifier."""

    return f"MCP-{uuid4().hex[:8].upper()}"


def build_ticket(payload: TicketCreate) -> TicketModel:
    """Build a database ticket from a validated request payload."""

    return TicketModel(
        id=create_ticket_id(),
        subject=payload.subject,
        body=payload.body,
        customer=payload.customer,
        customerEmail=str(payload.customerEmail),
        category=payload.category,
        priority="Low",
        sentiment="Neutral",
        sla="1 day",
        slaState="safe",
        status="Open",
        updatedAt="Just now",
        owner="Unassigned",
    )


def get_ticket_or_404(ticket_id: str, db: Session) -> TicketModel:
    """Return a ticket or raise the shared not-found response."""

    ticket = db.get(TicketModel, ticket_id)

    if ticket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found.",
        )

    return ticket


async def run_ticket_analysis(ticket_id: str) -> TicketAnalysisWorkflowResult:
    """Run one MCP analysis with a hard timeout."""

    return await asyncio.wait_for(
        analyze_ticket_with_mcp_workflow(ticket_id),
        timeout=ANALYSIS_TIMEOUT_SECONDS,
    )


async def run_ticket_analysis_job(ticket_id: str) -> None:
    """Run one background analysis and log failures without stopping a batch."""

    logger.info("Background MCP analysis started | ticket_id=%s", ticket_id)

    try:
        await run_ticket_analysis(ticket_id)
    except asyncio.TimeoutError:
        logger.exception(
            "Background MCP analysis timed out | ticket_id=%s "
            "| timeout_seconds=%s",
            ticket_id,
            ANALYSIS_TIMEOUT_SECONDS,
        )
    except Exception:  # noqa: BLE001 - background jobs must isolate failures
        logger.exception("Background MCP analysis failed | ticket_id=%s", ticket_id)
    else:
        logger.info("Background MCP analysis completed | ticket_id=%s", ticket_id)


async def run_bulk_ticket_analysis_job(ticket_ids: list[str]) -> None:
    """Analyze tickets concurrently while respecting the configured limit."""

    require_debug_mode()
    semaphore = asyncio.Semaphore(BULK_ANALYSIS_CONCURRENCY)

    async def analyze_one(ticket_id: str) -> None:
        async with semaphore:
            await run_ticket_analysis_job(ticket_id)

    await asyncio.gather(*(analyze_one(ticket_id) for ticket_id in ticket_ids))


def run_ticket_analysis_background(ticket_id: str) -> None:
    """Run one async analysis from a FastAPI background-task thread."""

    asyncio.run(run_ticket_analysis_job(ticket_id))


def run_bulk_ticket_analysis_background(ticket_ids: list[str]) -> None:
    """Run async bulk analysis from a FastAPI background-task thread."""

    require_debug_mode()
    asyncio.run(run_bulk_ticket_analysis_job(ticket_ids))


@router.get("", response_model=list[TicketRead])
def get_tickets(db: Session = Depends(get_db)) -> list[TicketModel]:
    """Return tickets ordered from newest to oldest."""

    statement = select(TicketModel).order_by(TicketModel.createdAt.desc())
    return list(db.scalars(statement).all())


@router.post(
    "",
    response_model=TicketRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a support ticket",
    description=(
        "Creates a support ticket and starts automatic MCP-based analysis "
        "in the background."
    ),
)
def create_ticket(
    payload: TicketCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> TicketModel:
    """Create one ticket and schedule its MCP analysis."""

    ticket = build_ticket(payload)

    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    background_tasks.add_task(run_ticket_analysis_background, ticket.id)

    return ticket


@router.post(
    "/bulk",
    response_model=TicketBulkCreateResult,
    status_code=status.HTTP_201_CREATED,
    summary="Create multiple support tickets",
    description=(
        "Creates up to 100 tickets in one transaction and optionally schedules "
        "MCP analysis with limited concurrency. Requires DEBUG=True."
    ),
)
def create_tickets_bulk(
    payload: TicketBulkCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> TicketBulkCreateResult:
    """Create multiple tickets and optionally schedule their MCP analyses."""

    require_debug_mode()
    tickets = [build_ticket(ticket_payload) for ticket_payload in payload.tickets]

    try:
        db.add_all(tickets)
        db.commit()
    except Exception:
        db.rollback()
        raise

    if payload.analyze:
        background_tasks.add_task(
            run_bulk_ticket_analysis_background,
            [ticket.id for ticket in tickets],
        )

    return TicketBulkCreateResult(
        createdCount=len(tickets),
        analysisScheduled=payload.analyze,
        tickets=[
            TicketRead.model_validate(ticket)  #list[TicketRead] != list[TicketModel]
            for ticket in tickets
        ],
    )


@router.post(
    "/{ticket_id}/analyze",
    response_model=TicketAnalysisWorkflowResult,
    summary="Analyze a ticket with MCP",
    description="Runs the MCP Host workflow manually for a selected ticket.",
)
async def analyze_ticket(
    ticket_id: str,
    db: Session = Depends(get_db),
) -> TicketAnalysisWorkflowResult:
    """Run MCP analysis synchronously for one ticket."""

    get_ticket_or_404(ticket_id, db)

    try:
        return await run_ticket_analysis(ticket_id)
    except asyncio.TimeoutError as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Ticket analysis timed out.",
        ) from exc


@router.get(
    "/{ticket_id}",
    response_model=TicketRead,
    summary="Get ticket details",
    description="Returns the full stored ticket data for the given ticket ID.",
)
def get_ticket(ticket_id: str, db: Session = Depends(get_db)) -> TicketModel:
    """Return one ticket by identifier."""

    return get_ticket_or_404(ticket_id, db)


@router.get(
    "/{ticket_id}/draft",
    response_model=ResponseDraftRead | None,
    summary="Get latest response draft",
    description=("Returns the latest saved AI-generated response draft for a ticket, if one exists."
    ),
)
def get_latest_ticket_draft(
    ticket_id: str,
    db: Session = Depends(get_db),
) -> ResponseDraftModel | None:
    """Return the newest response draft for an existing ticket."""

    get_ticket_or_404(ticket_id, db)

    statement = (
        select(ResponseDraftModel)
        .where(ResponseDraftModel.ticketId == ticket_id)
        .order_by(ResponseDraftModel.createdAt.desc())
        .limit(1)
    )
    return db.scalar(statement)
