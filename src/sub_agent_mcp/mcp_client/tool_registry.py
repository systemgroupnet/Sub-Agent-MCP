"""Tool discovery, filtering, and schema validation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from sub_agent_mcp.agent.errors import MCPConnectionError
from sub_agent_mcp.config.schema import AgentConfig
from sub_agent_mcp.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class ToolMetadata:
    """Sanitized tool metadata for downstream MCP tool discovery."""

    name: str
    server: str
    description: str
    qualified_name: str


def allows_all_tools(tool_allowlist: list[str] | None) -> bool:
    """Return True when no allowlist is configured (all tools permitted)."""
    return tool_allowlist is None


def qualified_tool_name(server_name: str, tool_name: str) -> str:
    """Build the server.tool qualified name used in allowlists."""
    return f"{server_name}.{tool_name}"


def is_tool_allowed(
    server_name: str,
    tool_name: str,
    allowlist: list[str] | None,
) -> bool:
    """Return True if the tool passes the allowlist filter."""
    if allows_all_tools(allowlist):
        return True
    return qualified_tool_name(server_name, tool_name) in allowlist


def validate_tool_schema(
    name: str,
    description: str | None,
    input_schema: dict[str, Any] | None,
) -> bool:
    """Validate that a tool has the minimum schema required for LangChain."""
    if not name or not name.strip():
        logger.warning("tool_rejected_empty_name")
        return False

    if not description or not description.strip():
        logger.warning("tool_rejected_empty_description", tool=name)
        return False

    if input_schema is None:
        return True

    if not isinstance(input_schema, dict):
        logger.warning("tool_rejected_invalid_schema", tool=name, reason="schema_not_object")
        return False

    schema_type = input_schema.get("type")
    if schema_type is not None and schema_type != "object":
        logger.warning("tool_rejected_invalid_schema", tool=name, reason="type_not_object")
        return False

    properties = input_schema.get("properties")
    if properties is not None and not isinstance(properties, dict):
        logger.warning("tool_rejected_invalid_schema", tool=name, reason="properties_not_object")
        return False

    return True


async def discover_tools(agent: AgentConfig) -> list[ToolMetadata]:
    """Discover and filter tools from all MCP servers configured for an agent."""
    discovered: list[ToolMetadata] = []

    for server in agent.mcp_servers:
        try:
            async with streamable_http_client(str(server.url)) as (read, write, _):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.list_tools()
                    for tool in result.tools:
                        if not is_tool_allowed(server.name, tool.name, agent.tool_allowlist):
                            continue

                        schema = tool.inputSchema if hasattr(tool, "inputSchema") else None
                        if not validate_tool_schema(tool.name, tool.description, schema):
                            continue

                        discovered.append(
                            ToolMetadata(
                                name=tool.name,
                                server=server.name,
                                description=tool.description or "",
                                qualified_name=qualified_tool_name(server.name, tool.name),
                            )
                        )
        except Exception as exc:
            logger.error(
                "mcp_server_unreachable",
                agent_id=agent.id,
                server=server.name,
                url=str(server.url),
                error=str(exc),
            )
            raise MCPConnectionError(
                f"MCP server '{server.name}' unreachable at {server.url}: {exc}"
            ) from exc

    return discovered


def filter_langchain_tools(
    tools: list[Any],
    agent: AgentConfig,
) -> list[Any]:
    """Filter LangChain tools using the agent allowlist."""
    if allows_all_tools(agent.tool_allowlist):
        return tools

    allowlist = set(agent.tool_allowlist or [])
    filtered: list[Any] = []

    for tool in tools:
        server_name = getattr(tool, "server_name", None) or getattr(tool, "metadata", {}).get(
            "server_name"
        )
        tool_name = getattr(tool, "name", None)

        if server_name and tool_name:
            qualified = qualified_tool_name(server_name, tool_name)
            if qualified in allowlist:
                filtered.append(tool)
            continue

        if tool_name and tool_name in allowlist:
            filtered.append(tool)

    return filtered
