"""MCP client manager for connecting to remote MCP servers."""

from __future__ import annotations

import os
from datetime import timedelta
from typing import Any

from langchain_mcp_adapters.client import MultiServerMCPClient

from sub_agent_mcp.agent.errors import MCPConnectionError
from sub_agent_mcp.config.schema import AgentConfig
from sub_agent_mcp.logging import get_logger
from sub_agent_mcp.mcp_client.tool_registry import allows_all_tools, qualified_tool_name

logger = get_logger(__name__)

DEFAULT_TIMEOUT = float(os.getenv("MCP_CLIENT_TIMEOUT", "30"))


def build_client_config(agent: AgentConfig) -> dict[str, dict[str, Any]]:
    """Build MultiServerMCPClient configuration from agent MCP server definitions."""
    timeout = timedelta(seconds=DEFAULT_TIMEOUT)
    return {
        server.name: {
            "transport": "streamable_http",
            "url": str(server.url),
            "headers": server.headers,
            "timeout": timeout,
        }
        for server in agent.mcp_servers
    }


def create_mcp_client(agent: AgentConfig) -> MultiServerMCPClient:
    """Create a MultiServerMCPClient for the given agent."""
    return MultiServerMCPClient(build_client_config(agent))


async def get_langchain_tools(agent: AgentConfig) -> list[Any]:
    """Connect to MCP servers and return allowlist-filtered LangChain tools."""
    if not agent.mcp_servers:
        return []

    client = create_mcp_client(agent)
    restrict_tools = not allows_all_tools(agent.tool_allowlist)
    allowlist = set(agent.tool_allowlist) if restrict_tools else None
    all_tools: list[Any] = []

    try:
        for server in agent.mcp_servers:
            server_tools = await client.get_tools(server_name=server.name)
            if allowlist is None:
                all_tools.extend(server_tools)
                continue

            for tool in server_tools:
                qualified = qualified_tool_name(server.name, tool.name)
                if qualified in allowlist:
                    all_tools.append(tool)

        logger.info(
            "mcp_tools_loaded",
            agent_id=agent.id,
            tool_count=len(all_tools),
        )
        return all_tools
    except Exception as exc:
        server_names = [server.name for server in agent.mcp_servers]
        logger.error(
            "mcp_connection_failed",
            agent_id=agent.id,
            servers=server_names,
            error=str(exc),
        )
        raise MCPConnectionError(
            f"Failed to connect to MCP servers for agent '{agent.id}': {exc}"
        ) from exc
