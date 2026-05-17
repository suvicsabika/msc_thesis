"""MCP client wrapper for the local Ticket MCP Server.

This module implements the Host-side MCP client connection. It starts the local
MCP Ticket Server through stdio transport, initializes a ClientSession, and
provides helper methods for resource reads and tool calls.
"""

import asyncio
import json
import logging
import os
import sys
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from pydantic import AnyUrl


logger = logging.getLogger(__name__)


class TicketMcpClient:
    """Manage a subprocess-backed MCP client session for ticket analysis."""
    def __init__(self) -> None:
        self.exit_stack = AsyncExitStack()
        self.session: ClientSession | None = None

    async def __aenter__(self) -> "TicketMcpClient":
        """Start the local MCP Ticket Server subprocess and initialize the client session."""

        backend_dir = Path(__file__).resolve().parents[2]

        env = dict(os.environ)
        env["PYTHONPATH"] = str(backend_dir)

        logger.info("Starting MCP Ticket Server subprocess")

        server_params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "app.mcp.ticket_server"],
            env=env,
        )

        read_stream, write_stream = await self.exit_stack.enter_async_context(
            stdio_client(server_params)
        )

        self.session = await self.exit_stack.enter_async_context(
            ClientSession(read_stream, write_stream)
        )

        await self.session.initialize()

        logger.info("MCP client session initialized")

        return self

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        """Close the MCP client session and shut down the subprocess cleanly."""

        logger.info("Closing MCP client session")

        try:
            await asyncio.wait_for(self.exit_stack.aclose(), timeout=10)

            logger.info("MCP client session closed")

        except asyncio.TimeoutError:
            logger.exception("MCP client session close timed out")

        except Exception:
            logger.exception("MCP client session close failed")
            raise

    def require_session(self) -> ClientSession:
        """Return the active client session or raise if the client is not initialized."""

        if self.session is None:
            raise RuntimeError("MCP client session has not been initialized.")

        return self.session

    async def read_resource_text(self, uri: str) -> str:
        """Fetch a resource from the MCP server and return its text content."""

        session = self.require_session()

        logger.info("Reading MCP resource | uri=%s", uri)

        result = await session.read_resource(AnyUrl(uri))

        texts = []

        for content in result.contents:
            text = getattr(content, "text", None)

            if text is not None:
                texts.append(text)

        logger.info("MCP resource read completed | uri=%s", uri)

        return "\n".join(texts)

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Invoke the named MCP tool with the provided arguments."""

        session = self.require_session()

        result = await session.call_tool(name, arguments)

        return {
            "tool": name,
            "arguments": arguments,
            "result": self.serialize_tool_result(result),
        }

    def serialize_tool_result(self, result) -> dict[str, Any]:
        """Convert MCP tool results to a JSON-serializable dictionary."""

        structured_content = getattr(result, "structuredContent", None)

        if structured_content is not None:
            return {
                "structuredContent": structured_content,
            }

        texts = []

        for content in getattr(result, "content", []):
            text = getattr(content, "text", None)

            if text is not None:
                try:
                    texts.append(json.loads(text))
                except json.JSONDecodeError:
                    texts.append(text)

        return {
            "content": texts,
        }