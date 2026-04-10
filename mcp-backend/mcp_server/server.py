from fastmcp import FastMCP

from mcp_server.capabilities.tools import register_tools
from mcp_server.capabilities.resources import register_resources
from mcp_server.capabilities.prompts import register_prompts
from mcp_server.utils.config import settings

mcp = FastMCP(
    name="Valorant Analysis MCP Server",
    instructions=(
        "Provides tools and resources for analyzing Valorant match videos. "
        "Start with analyze_video(), then compute_round_stats(), then generate_tactical_summary()."
    ),
)

register_tools(mcp)
register_resources(mcp)
register_prompts(mcp)

if __name__ == "__main__":
    # Default: stdio. Switch to HTTP later if needed.
    if settings.mcp_transport == "http":
        mcp.run(
            transport="http",
            host=settings.mcp_host,
            port=settings.mcp_port,
        )
    else:
        mcp.run()