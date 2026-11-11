"""MCP registration for the shared ticket operations."""

from mcp.server import MCPServer

from app.mcp.prompts import build_ticket_triage_prompt
from app.services.ticket_operations import (
    save_response_draft,
    set_ticket_classification,
    set_ticket_priority,
    set_ticket_sentiment,
    ticket_classification_resource,
    ticket_draft_response_resource,
    ticket_history_resource,
    ticket_priority_resource,
    ticket_raw_resource,
    tickets_index_resource,
)


mcp = MCPServer("mcp-ticket-analyzer", version="2.2.0")

mcp.resource("tickets://index")(tickets_index_resource)
mcp.resource("ticket://{ticket_id}/raw")(ticket_raw_resource)
mcp.resource("ticket://{ticket_id}/classification")(
    ticket_classification_resource
)
mcp.resource("ticket://{ticket_id}/priority")(ticket_priority_resource)
mcp.resource("ticket://{ticket_id}/draft_response")(
    ticket_draft_response_resource
)
mcp.resource("ticket://{ticket_id}/history")(ticket_history_resource)
mcp.tool()(set_ticket_classification)
mcp.tool()(set_ticket_sentiment)
mcp.tool()(set_ticket_priority)
mcp.tool()(save_response_draft)


@mcp.prompt()
def ticket_triage_prompt(ticket_id: str) -> str:
    """Start ticket triage using the available resources and tools."""

    return build_ticket_triage_prompt(ticket_id)


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
