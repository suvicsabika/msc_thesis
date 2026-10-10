"""Ticket analysis workflow service.

This module represents the Host-side MCP orchestration layer. It
connects to the local MCP Ticket Server, retrieves a triage prompt with
ticket context, sends the messages to OpenAI for structured triage, and
persists the decision through MCP tool calls.
"""

import asyncio
import logging
from collections.abc import Awaitable
from typing import Any, TypeVar

from app.ai.openai_client import analyze_ticket_with_openai
from app.ai.schemas import TicketAnalysisWorkflowResult
from app.mcp.client import TicketMcpClient


logger = logging.getLogger(__name__)

MCP_STEP_TIMEOUT_SECONDS = 10
OPENAI_STEP_TIMEOUT_SECONDS = 15
StepResult = TypeVar("StepResult")


async def run_step(
    label: str,
    awaitable: Awaitable[StepResult],
    timeout_seconds: int = MCP_STEP_TIMEOUT_SECONDS,
) -> StepResult:
    """Run a workflow step with logging and a timeout."""

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


async def analyze_ticket_with_mcp_workflow(
    ticket_id: str,
) -> TicketAnalysisWorkflowResult:
    """Analyze a ticket through the MCP Host-Client-Server workflow.

    Steps:
    1. Connect over stdio and discover the MCP server using SDK v2.
    2. Retrieve the MCP triage prompt with its ticket context.
    3. Send the prompt messages to OpenAI.
    4. Receive a structured triage decision.
    5. Persist the decision through MCP tool calls.
    6. Return the decision and tool execution results.
    """

    logger.info("MCP workflow started | ticket_id=%s", ticket_id)

    async with TicketMcpClient() as mcp_client:
        logger.info("MCP client connected | ticket_id=%s", ticket_id)

        prompt_messages = await run_step(
            label="get_ticket_triage_prompt",
            awaitable=mcp_client.get_prompt_messages(
                "ticket_triage_prompt", {"ticket_id": ticket_id}
            ),
        )

        logger.info("OpenAI analysis step started | ticket_id=%s", ticket_id)

        decision = await asyncio.wait_for(
            asyncio.to_thread(
                analyze_ticket_with_openai, ticket_id, prompt_messages
            ),
            timeout=OPENAI_STEP_TIMEOUT_SECONDS,
        )

        logger.info(
            "OpenAI analysis step completed | ticket_id=%s | category=%s "
            "| sentiment=%s | priority=%s",
            ticket_id,
            decision.category,
            decision.sentiment,
            decision.priority,
        )

        tool_calls = [
            (
                "set_ticket_classification",
                {
                    "category": decision.category,
                    "confidence": decision.classificationConfidence,
                    "reason": decision.classificationReason,
                },
            ),
            (
                "set_ticket_sentiment",
                {
                    "sentiment": decision.sentiment,
                    "score": decision.sentimentScore,
                    "reason": decision.sentimentReason,
                },
            ),
            (
                "set_ticket_intent",
                {
                    "intent": decision.customerIntent,
                    "confidence": decision.intentConfidence,
                },
            ),
            (
                "set_ticket_priority",
                {
                    "priority": decision.priority,
                    "sla": decision.sla,
                    "sla_state": decision.slaState,
                    "confidence": decision.priorityConfidence,
                    "reason": decision.priorityReason,
                },
            ),
            (
                "save_response_draft",
                {
                    "draft": decision.responseDraft,
                    "requires_approval": True,
                    "reason": decision.responseDraftReason,
                },
            ),
        ]

        # Sequential writes stop the remaining steps after a failure.
        tool_results = []
        for tool_name, arguments in tool_calls:
            result = await call_mcp_tool_logged(
                mcp_client, tool_name, {"ticket_id": ticket_id, **arguments}
            )
            tool_results.append(result)

        logger.info("MCP workflow completed | ticket_id=%s", ticket_id)

        return TicketAnalysisWorkflowResult(
            ticketId=ticket_id,
            decision=decision,
            mcpToolResults=tool_results,
        )
