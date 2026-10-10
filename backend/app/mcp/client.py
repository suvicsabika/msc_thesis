"""Host-side MCP client for the local Ticket MCP Server over stdio.

The SDK manages server discovery and subprocess lifetime. This wrapper
validates server capabilities and exposes text resources and tool
results.
"""

import logging
import os
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from mcp import Client, StdioServerParameters
from mcp.types import (
    CallToolResult,
    Implementation,
    PromptMessage,
    TextContent,
    TextResourceContents,
)


logger = logging.getLogger(__name__)

APP_DIR = Path(__file__).resolve().parents[1]
try:
    load_dotenv(APP_DIR / ".env", override=False)
except (OSError, ValueError):
    logger.warning(
        "Could not load optional .env settings; using the current environment."
    )

MCP_PROTOCOL_VERSION = os.getenv("MCP_PROTOCOL_VERSION", "2026-07-28")


class TicketMcpClient:
    """Manage the SDK client and subprocess for one ticket workflow."""

    def __init__(self) -> None:
        self.client: Client | None = None

    async def __aenter__(self) -> "TicketMcpClient":
        """Connect and discover the server capabilities."""

        if self.client is not None:
            raise RuntimeError("MCP client is already connected.")

        backend_dir = Path(__file__).resolve().parents[2]

        env = dict(os.environ)
        env["PYTHONPATH"] = os.pathsep.join(
            filter(None, [str(backend_dir), env.get("PYTHONPATH")])
        )

        server_params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "app.mcp.ticket_server"],
            cwd=backend_dir,
            env=env,
        )

        client = Client(
            server_params,
            mode="auto",
            read_timeout_seconds=25.0,
            client_info=Implementation(
                name="mcp-ticket-analyzer-host", version="0.1.0"
            ),
        )
        logger.info("Starting MCP Ticket Server subprocess")
        await client.__aenter__()
        try:
            if client.protocol_version != MCP_PROTOCOL_VERSION:
                raise RuntimeError(
                    f"Expected MCP {MCP_PROTOCOL_VERSION}, "
                    f"got {client.protocol_version}. "
                    "Install the project's SDK v2 requirements "
                    "in both host and server."
                )
            capabilities = client.server_capabilities
            if (
                capabilities.tools is None
                or capabilities.resources is None
                or capabilities.prompts is None
            ):
                raise RuntimeError(
                    "Ticket MCP Server must provide tools, resources, "
                    "and prompts."
                )
        except BaseException:
            await client.__aexit__(None, None, None)
            raise

        self.client = client
        logger.info(
            "MCP server discovered | protocol_version=%s | server_info=%s",
            client.protocol_version,
            client.server_info,
        )

        return self

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        """Close the SDK client in the task that opened it."""

        client = self.require_client()
        logger.info("Closing MCP client session")

        try:
            # Passing host exceptions into SDK task groups wraps them in
            # ExceptionGroup and hides the workflow's TimeoutError.
            await client.__aexit__(None, None, None)
        finally:
            self.client = None
        logger.info("MCP client connection closed")

    def require_client(self) -> Client:
        """Return the connected SDK client or fail before issuing a
        request.
        """
        if self.client is None:
            raise RuntimeError("MCP client is not connected.")
        return self.client

    async def read_resource_text(self, uri: str) -> str:
        """Read a string URI and return the resource's text contents."""

        logger.info("Reading MCP resource | uri=%s", uri)

        result = await self.require_client().read_resource(uri)
        texts = [
            item.text
            for item in result.contents
            if isinstance(item, TextResourceContents)
        ]
        if not texts:
            raise RuntimeError(f"MCP resource contains no text: {uri}")
        logger.info("MCP resource read completed | uri=%s", uri)

        return "\n".join(texts)

    async def get_prompt_messages(
        self, name: str, arguments: dict[str, str]
    ) -> list[PromptMessage]:
        """Retrieve rendered MCP messages for the model request."""

        result = await self.require_client().get_prompt(name, arguments)
        if not result.messages:
            raise RuntimeError(f"MCP prompt contains no messages: {name}")
        return result.messages

    async def call_tool(
        self, name: str, arguments: dict[str, Any]
    ) -> dict[str, Any]:
        """Call a tool and stop on an MCP execution error."""

        result = await self.require_client().call_tool(name, arguments)
        if result.is_error:
            detail = "\n".join(
                item.text
                for item in result.content
                if isinstance(item, TextContent)
            )
            raise RuntimeError(f"MCP tool {name} failed: {detail}")

        return {
            "tool": name,
            "arguments": arguments,
            "result": self.serialize_tool_result(result),
        }

    @staticmethod
    def serialize_tool_result(result: CallToolResult) -> dict[str, Any]:
        """Keep MCP's camelCase JSON aliases for the REST API and
        frontend.
        """
        return result.model_dump(mode="json", by_alias=True, exclude_none=True)
