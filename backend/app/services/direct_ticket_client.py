"""In-process ticket operations with no MCP dependency or subprocess."""

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from jsonschema import validate

from app.ai.schemas import TicketAnalysisWorkflowResult
from app.ai.triage_prompt import build_ticket_triage_prompt
from app.services import ticket_operations as operations


CATALOG_PATH = Path(__file__).with_name("direct_ticket_catalog.json")
TOOLS = {
    name: getattr(operations, name)
    for name in (
        "set_ticket_classification",
        "set_ticket_sentiment",
        "set_ticket_priority",
        "save_response_draft",
    )
}
RESOURCES = {
    "raw": operations.ticket_raw_resource,
    "classification": operations.ticket_classification_resource,
    "priority": operations.ticket_priority_resource,
    "draft_response": operations.ticket_draft_response_resource,
    "history": operations.ticket_history_resource,
}


class DirectTicketClient:
    """Call ticket operations directly."""

    async def discover_catalog(self) -> dict[str, list[dict[str, Any]]]:
        """Load the frozen catalog to keep model inputs comparable."""
        return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))

    async def get_prompt_messages(
        self, name: str, arguments: dict[str, str]
    ) -> list[SimpleNamespace]:
        if name != "ticket_triage_prompt":
            raise ValueError(f"Unknown prompt: {name}")
        return [
            SimpleNamespace(
                role="user",
                content=SimpleNamespace(
                    type="text",
                    text=build_ticket_triage_prompt(**arguments),
                ),
            )
        ]

    async def read_resource_text(self, uri: str) -> str:
        ticket_id, separator, suffix = uri.removeprefix(
            "ticket://"
        ).rpartition("/")
        if not uri.startswith("ticket://") or separator != "/":
            raise ValueError(f"Unknown ticket resource: {uri}")
        if suffix not in RESOURCES or not ticket_id or "/" in ticket_id:
            raise ValueError(f"Unknown ticket resource: {uri}")
        return await asyncio.to_thread(RESOURCES[suffix], ticket_id)

    async def call_tool(
        self, name: str, arguments: dict[str, Any]
    ) -> dict[str, Any]:
        if name not in TOOLS:
            raise ValueError(f"Unknown saving function: {name}")
        catalog = await self.discover_catalog()
        definition = next(t for t in catalog["tools"] if t["name"] == name)
        validate(arguments, definition["inputSchema"])
        result = await asyncio.to_thread(TOOLS[name], **arguments)
        # Retain the model-visible envelope of the original workflow.
        return {
            "tool": name,
            "arguments": arguments,
            "result": {
                "_meta": {
                    "io.modelcontextprotocol/serverInfo": {
                        "name": "mcp-ticket-analyzer",
                        "version": "2.2.0",
                    }
                },
                "content": [
                    {"type": "text", "text": json.dumps(result, indent=2)}
                ],
                "isError": False,
                "resultType": "complete",
            },
        }


async def analyze_ticket_with_direct_workflow(
    ticket_id: str,
) -> TicketAnalysisWorkflowResult:
    """Use the shared model loop without constructing an MCP client."""
    from app.services.ticket_analysis_workflow import (
        analyze_ticket_with_client,
    )

    result = await analyze_ticket_with_client(ticket_id, DirectTicketClient())
    result.transport = "direct"
    return result
