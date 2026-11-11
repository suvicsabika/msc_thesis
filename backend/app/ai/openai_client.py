"""OpenAI requests for the host's model-directed MCP workflow."""

import logging
import os
from pathlib import Path
from typing import Any, cast

from dotenv import load_dotenv
from openai import AsyncOpenAI
from openai.types.responses import (
    FunctionToolParam,
    Response,
    ResponseInputItemParam,
    ResponseInputParam,
    ResponseOutputItem,
)

from app.ai.schemas import TicketTriageDecision
from app.core.timeouts import OPERATION_TIMEOUT_SECONDS


logger = logging.getLogger(__name__)

Conversation = list[ResponseInputItemParam | ResponseOutputItem]

APP_DIR = Path(__file__).resolve().parents[1]
try:
    load_dotenv(APP_DIR / ".env", override=False)
except (OSError, ValueError):
    logger.warning(
        "Could not load optional .env settings; using the current environment."
    )


def get_openai_client() -> AsyncOpenAI:
    """Create an asynchronous client with explicit workflow timeouts."""

    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_ADMIN_KEY")
    if not api_key:
        raise FileNotFoundError(
            "Ticket analysis is unavailable. "
            "Configure OPENAI_API_KEY on the server."
        )

    return AsyncOpenAI(
        api_key=api_key, max_retries=0, timeout=OPERATION_TIMEOUT_SECONDS
    )


def get_analysis_model() -> str:
    """Return the configured ticket analysis model."""

    return os.getenv("OPENAI_MODEL", "gpt-6-luna")


def to_openai_tools(tools: list[dict[str, Any]]) -> list[FunctionToolParam]:
    """Adapt discovered MCP definitions to OpenAI function tools."""

    return [
        {
            "type": "function",
            "name": tool["name"],
            "description": tool.get("description", ""),
            "parameters": tool["inputSchema"],
            # Keep arbitrary MCP schemas; the host validates arguments.
            "strict": False,
        }
        for tool in tools
    ]


async def request_ticket_step(
    client: AsyncOpenAI,
    ticket_id: str,
    messages: Conversation,
    tools: list[FunctionToolParam],
) -> Response:
    """Request calls or a final decision in the same conversation."""

    response = await client.responses.create(
        model=get_analysis_model(),
        # Output models are valid inputs despite the dict-only SDK type.
        input=cast(ResponseInputParam, messages),
        tools=tools,
        tool_choice="auto",
        parallel_tool_calls=True,
        text={
            "format": {
                "type": "json_schema",
                "name": "ticket_triage_decision",
                "schema": TicketTriageDecision.model_json_schema(),
                "strict": True,
            }
        },
    )
    usage = response.usage
    logger.info(
        "OpenAI workflow step completed | ticket_id=%s | response_id=%s "
        "| total_tokens=%s",
        ticket_id,
        response.id,
        usage.total_tokens if usage is not None else None,
    )
    return response
