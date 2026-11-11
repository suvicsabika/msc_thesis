"""Model-directed MCP resource reads and ticket writes over stdio."""

import asyncio
import json
import logging
from collections.abc import Awaitable
from typing import TYPE_CHECKING, Any, TypeVar

from jsonschema import validate

from app.ai.openai_client import (
    Conversation,
    get_openai_client,
    request_ticket_step,
    to_openai_tools,
)
from app.ai.prompts import TRIAGE_SYSTEM_PROMPT
from app.ai.schemas import (
    TicketAnalysisWorkflowResult,
    TicketTokenUsage,
    TicketTriageDecision,
)
from app.core.timeouts import OPERATION_TIMEOUT_SECONDS


if TYPE_CHECKING:
    from app.mcp.client import TicketMcpClient
    from app.services.direct_ticket_client import DirectTicketClient


logger = logging.getLogger(__name__)

MAX_MODEL_ROUNDS = 12
READ_RESOURCE_TOOL = "read_mcp_resource"
REQUIRED_TOOLS = {
    "set_ticket_classification",
    "set_ticket_sentiment",
    "set_ticket_priority",
    "save_response_draft",
}
StepResult = TypeVar("StepResult")


async def run_step(
    label: str,
    awaitable: Awaitable[StepResult],
    timeout_seconds: int = OPERATION_TIMEOUT_SECONDS,
) -> StepResult:
    """Run a workflow step with logging and a timeout."""

    logger.info("Workflow step started | step=%s", label)
    try:
        result = await asyncio.wait_for(awaitable, timeout=timeout_seconds)
    except asyncio.TimeoutError:
        logger.exception(
            "Workflow step timed out | step=%s | timeout_seconds=%s",
            label,
            timeout_seconds,
        )
        raise
    logger.info("Workflow step completed | step=%s", label)
    return result


async def call_mcp_tool_logged(
    mcp_client: "TicketMcpClient | DirectTicketClient",
    tool_name: str,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """Execute the model's selected MCP tool with a timeout."""

    logger.info(
        "MCP tool call | tool=%s | ticket_id=%s",
        tool_name,
        arguments.get("ticket_id"),
    )

    return await run_step(
        label=f"mcp_tool:{tool_name}",
        awaitable=mcp_client.call_tool(tool_name, arguments),
    )


def validate_completion(
    decision: TicketTriageDecision, tool_results: list[dict[str, Any]]
) -> None:
    """Check that the final decision matches the successful saves."""

    expected = {
        "set_ticket_classification": {
            "category": decision.category,
            "confidence": decision.classificationConfidence,
            "reason": decision.classificationReason,
        },
        "set_ticket_sentiment": {
            "sentiment": decision.sentiment,
            "score": decision.sentimentScore,
            "reason": decision.sentimentReason,
        },
        "set_ticket_priority": {
            "priority": decision.priority,
            "sla": decision.sla,
            "confidence": decision.priorityConfidence,
            "reason": decision.priorityReason,
        },
        "save_response_draft": {
            "draft": decision.responseDraft,
            "requires_approval": True,
            "reason": decision.responseDraftReason,
        },
    }
    completed = {item["tool"]: item["arguments"] for item in tool_results}
    missing = REQUIRED_TOOLS - completed.keys()
    if missing:
        raise RuntimeError(f"Missing successful MCP saves: {sorted(missing)}")
    for name, fields in expected.items():
        if any(
            completed[name].get(key) != value for key, value in fields.items()
        ):
            raise RuntimeError(
                f"Final decision differs from saved data: {name}"
            )


async def analyze_ticket_with_mcp_workflow(
    ticket_id: str,
) -> TicketAnalysisWorkflowResult:
    """Let the model choose resource reads and saving tools."""

    from app.mcp.client import TicketMcpClient

    async with TicketMcpClient() as mcp_client:
        return await analyze_ticket_with_client(ticket_id, mcp_client)


async def analyze_ticket_with_client(
    ticket_id: str, mcp_client: "TicketMcpClient | DirectTicketClient"
) -> TicketAnalysisWorkflowResult:
    """Run the same model loop using either operation adapter."""

    catalog = await run_step("discover_catalog", mcp_client.discover_catalog())
    definitions = {tool["name"]: tool for tool in catalog["tools"]}
    if READ_RESOURCE_TOOL in definitions:
        raise RuntimeError("MCP tool name conflicts with resource adapter.")
    if not REQUIRED_TOOLS.issubset(definitions):
        raise RuntimeError("MCP server is missing required saving tools.")

    # Scope resource reads to this ticket.
    readable_uris = {
        item["uriTemplate"].replace("{ticket_id}", ticket_id)
        for item in catalog["resourceTemplates"]
        if "{ticket_id}" in item["uriTemplate"]
    }
    readable_uris.update(
        item["uri"]
        for item in catalog["resources"]
        if item["uri"].startswith(f"ticket://{ticket_id}/")
    )
    raw_uri = f"ticket://{ticket_id}/raw"
    if raw_uri not in readable_uris:
        raise RuntimeError("MCP catalog is missing the raw ticket resource.")
    reader_schema = {
        "type": "object",
        "properties": {
            "uri": {"type": "string", "enum": sorted(readable_uris)}
        },
        "required": ["uri"],
        "additionalProperties": False,
    }
    tools = to_openai_tools(catalog["tools"])
    tools.append(
        {
            "type": "function",
            "name": READ_RESOURCE_TOOL,
            "description": (
                "Read an allowed resource URI using MCP resources/read. "
                "Select the URI using the supplied resource catalog."
            ),
            "parameters": reader_schema,
            "strict": True,
        }
    )
    prompt_messages = await run_step(
        "get_ticket_triage_prompt",
        mcp_client.get_prompt_messages(
            "ticket_triage_prompt", {"ticket_id": ticket_id}
        ),
    )
    messages: Conversation = [
        {"role": "system", "content": TRIAGE_SYSTEM_PROMPT}
    ]
    for message in prompt_messages:
        content = message.content
        if content.type != "text":
            raise ValueError("Ticket triage requires text prompt messages.")
        messages.append(
            {
                "role": message.role,
                "content": content.text,
            }
        )
    messages.append(
        {
            "role": "user",
            "content": json.dumps(
                {
                    "ticketId": ticket_id,
                    "catalog": catalog,
                    "readableResourceUris": sorted(readable_uris),
                }
            ),
        }
    )

    tool_results = []
    resource_reads = []
    completed_tools = set()
    usage = TicketTokenUsage(input_tokens=0, output_tokens=0, total_tokens=0)
    usage_complete = True
    async with get_openai_client() as ai_client:
        for round_index in range(MAX_MODEL_ROUNDS):
            response = await run_step(
                f"model_round:{round_index + 1}",
                request_ticket_step(ai_client, ticket_id, messages, tools),
            )
            if response.status != "completed":
                raise RuntimeError("OpenAI workflow response is incomplete.")
            if response.usage is None:
                usage_complete = False
            else:
                usage.input_tokens += response.usage.input_tokens
                usage.output_tokens += response.usage.output_tokens
                usage.total_tokens += response.usage.total_tokens
            messages.extend(response.output)
            calls = [
                item
                for item in response.output
                if item.type == "function_call"
            ]
            if not calls:
                if raw_uri not in resource_reads:
                    raise RuntimeError("Model did not read the raw ticket.")
                decision = TicketTriageDecision.model_validate_json(
                    response.output_text
                )
                validate_completion(decision, tool_results)
                return TicketAnalysisWorkflowResult(
                    ticketId=ticket_id,
                    decision=decision,
                    mcpToolResults=tool_results,
                    mcpResourceReads=resource_reads,
                    usage=usage if usage_complete else None,
                )

            # Execute all returned calls sequentially.
            for call in calls:
                arguments = json.loads(call.arguments)
                if call.name == READ_RESOURCE_TOOL:
                    validate(arguments, reader_schema)
                    uri = arguments["uri"]
                    output = await run_step(
                        "read_resource", mcp_client.read_resource_text(uri)
                    )
                    resource_reads.append(uri)
                else:
                    if call.name not in definitions:
                        raise ValueError(f"Unknown MCP tool: {call.name}")
                    validate(arguments, definitions[call.name]["inputSchema"])
                    if arguments.get("ticket_id") != ticket_id:
                        raise ValueError("Tool targets a different ticket.")
                    if raw_uri not in resource_reads:
                        raise RuntimeError(
                            "Read the raw ticket before saving."
                        )
                    if call.name in completed_tools:
                        raise RuntimeError(f"Duplicate MCP save: {call.name}")
                    result = await call_mcp_tool_logged(
                        mcp_client, call.name, arguments
                    )
                    tool_results.append(result)
                    completed_tools.add(call.name)
                    output = json.dumps(result["result"])
                messages.append(
                    {
                        "type": "function_call_output",
                        "call_id": call.call_id,
                        "output": output,
                    }
                )
    raise RuntimeError("Model exceeded the MCP workflow round limit.")
