"""FastMCP server entry point."""

from __future__ import annotations

import os
import sys

from mcp.server.fastmcp import FastMCP

from sub_agent_mcp.config.errors import ConfigError
from sub_agent_mcp.config.loader import load_agents_config
from sub_agent_mcp.logging import setup_logging
from sub_agent_mcp.server.tools import register_tools


def create_app() -> FastMCP:
    """Create and configure the FastMCP application."""
    setup_logging(os.getenv("LOG_LEVEL", "INFO"))

    try:
        config = load_agents_config()
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    mcp = FastMCP(
        "SubAgentMCP",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        stateless_http=True,
        json_response=True,
    )

    register_tools(mcp, config)
    return mcp


def main() -> None:
    """Run the MCP server with Streamable HTTP transport."""
    mcp = create_app()
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
