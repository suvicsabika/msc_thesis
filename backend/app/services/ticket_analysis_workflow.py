"""Ticket analysis workflow service.

This module represents the Host-side MCP orchestration layer.
It connects to the local MCP Ticket Server, reads ticket context through MCP
resources, sends the context to OpenAI for structured triage, and persists the
decision through MCP tool calls.
"""

import asyncio
import logging
from typing import Any

from pydantic import AnyUrl

from app.ai.openai_client import analyze_ticket_with_openai
from app.ai.schemas import TicketAnalysisWorkflowResult
from app.mcp.client import TicketMcpClient


logger = logging.getLogger(__name__)

MCP_STEP_TIMEOUT_SECONDS = 25
OPENAI_STEP_TIMEOUT_SECONDS = 60


async def run_step(label: str, awaitable, timeout_seconds: int = MCP_STEP_TIMEOUT_SECONDS):
    """Run an async workflow step with logging and timeout protection."""

    logger.info("Workflow step started | step=%s", label)

    try:
        result = await asyncio.wait_for(awaitable, timeout=timeout_seconds)

        logger.info("Workflow step completed | step=%s", label)

        return result

    except asyncio.TimeoutError:
        logger.exception(
            "Workflow step timed out | step=%s | timeout_seconds=%s",
            label,
            timeout_seconds,
        )
        raise


async def call_mcp_tool_logged(
    mcp_client: TicketMcpClient,
    tool_name: str,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """Call an MCP tool with structured logging."""

    logger.info(
        "MCP tool call started | tool=%s | ticket_id=%s",
        tool_name,
        arguments.get("ticket_id"),
    )

    result = await run_step(
        label=f"mcp_tool:{tool_name}",
        awaitable=mcp_client.call_tool(tool_name, arguments),
    )

    logger.info(
        "MCP tool call completed | tool=%s | ticket_id=%s",
        tool_name,
        arguments.get("ticket_id"),
    )

    return result


async def analyze_ticket_with_mcp_workflow(ticket_id: str) -> TicketAnalysisWorkflowResult:
    """Analyze a ticket through the MCP Host-Client-Server workflow.

    Steps:
    1. Start an MCP client session over stdio.
    2. Read the raw ticket resource from the MCP server.
    3. Send the ticket context to OpenAI.
    4. Receive a structured triage decision.
    5. Persist the decision through MCP tool calls.
    6. Return the decision and tool execution results.
    """

    logger.info("MCP workflow started | ticket_id=%s", ticket_id)

    async with TicketMcpClient() as mcp_client:
        logger.info("MCP client connected | ticket_id=%s", ticket_id)

        ticket_json = await run_step(
            label="read_ticket_raw_resource",
            awaitable=mcp_client.read_resource_text(f"ticket://{ticket_id}/raw"),
        )

        logger.info("OpenAI analysis step started | ticket_id=%s", ticket_id)

        decision = await asyncio.wait_for(
            asyncio.to_thread(analyze_ticket_with_openai, ticket_id, ticket_json),
            timeout=OPENAI_STEP_TIMEOUT_SECONDS,
        )

        logger.info(
            "OpenAI analysis step completed | ticket_id=%s | category=%s | sentiment=%s | priority=%s",
            ticket_id,
            decision.category,
            decision.sentiment,
            decision.priority,
        )

        tool_results = []

        tool_results.append(
            await call_mcp_tool_logged(
                mcp_client,
                "set_ticket_classification",
                {
                    "ticket_id": ticket_id,
                    "category": decision.category,
                    "confidence": decision.classificationConfidence,
                    "reason": decision.classificationReason,
                },
            )
        )

        tool_results.append(
            await call_mcp_tool_logged(
                mcp_client,
                "set_ticket_sentiment",
                {
                    "ticket_id": ticket_id,
                    "sentiment": decision.sentiment,
                    "score": decision.sentimentScore,
                    "reason": decision.sentimentReason,
                },
            )
        )

        tool_results.append(
            await call_mcp_tool_logged(
                mcp_client,
                "set_ticket_intent",
                {
                    "ticket_id": ticket_id,
                    "intent": decision.customerIntent,
                    "confidence": decision.intentConfidence,
                },
            )
        )

        tool_results.append(
            await call_mcp_tool_logged(
                mcp_client,
                "set_ticket_priority",
                {
                    "ticket_id": ticket_id,
                    "priority": decision.priority,
                    "sla": decision.sla,
                    "sla_state": decision.slaState,
                    "confidence": decision.priorityConfidence,
                    "reason": decision.priorityReason,
                },
            )
        )

        tool_results.append(
            await call_mcp_tool_logged(
                mcp_client,
                "save_response_draft",
                {
                    "ticket_id": ticket_id,
                    "draft": decision.responseDraft,
                    "requires_approval": True,
                    "reason": decision.responseDraftReason,
                },
            )
        )

        logger.info("MCP workflow completed | ticket_id=%s", ticket_id)

        return TicketAnalysisWorkflowResult(
            ticketId=ticket_id,
            decision=decision,
            mcpToolResults=tool_results,
        )