"""MCP tool handlers exposed by this server."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from sub_agent_mcp.agent.errors import AgentError, AgentNotFoundError
from sub_agent_mcp.agent.executor import spawn_agent as run_spawn_agent
from sub_agent_mcp.config.schema import AgentsFile
from sub_agent_mcp.logging import get_logger
from sub_agent_mcp.mcp_client.tool_registry import discover_tools

logger = get_logger(__name__)


def register_tools(mcp: FastMCP, config: AgentsFile) -> None:
    """Register list_agents and spawn_agent tools on the MCP server."""

    @mcp.tool()
    async def list_agents() -> list[dict[str, Any]]:
        """List all configured sub-agents with their MCP servers and available tools."""
        agents_output: list[dict[str, Any]] = []

        for agent in config.agents:
            try:
                tools = await discover_tools(agent)
            except AgentError as exc:
                logger.warning(
                    "list_agents_tool_discovery_failed",
                    agent_id=agent.id,
                    error=str(exc),
                )
                tools = []

            agents_output.append(
                {
                    "id": agent.id,
                    "title": agent.title,
                    "description": agent.description,
                    "model_id": agent.llm.model_id,
                    "base_uri": str(agent.llm.base_uri),
                    "mcp_servers": [
                        {"name": server.name, "url": str(server.url)}
                        for server in agent.mcp_servers
                    ],
                    "available_tools": [
                        {
                            "name": tool.name,
                            "server": tool.server,
                            "description": tool.description,
                            "qualified_name": tool.qualified_name,
                        }
                        for tool in tools
                    ],
                }
            )

        return agents_output

    @mcp.tool()
    async def spawn_agent(agent_id: str, prompt: str) -> dict[str, str]:
        """Spawn a sub-agent by id and run it with the given prompt."""
        try:
            response = await run_spawn_agent(config, agent_id, prompt)
            return {"response": response}
        except AgentNotFoundError as exc:
            return {"error": str(exc)}
        except AgentError as exc:
            logger.error("spawn_agent_tool_error", agent_id=agent_id, error=str(exc))
            return {"error": str(exc)}
