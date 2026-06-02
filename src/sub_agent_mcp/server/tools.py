"""MCP tool handlers exposed by this server."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from sub_agent_mcp.agent.errors import AgentError, AgentNotFoundError
from sub_agent_mcp.agent.executor import spawn_agent as run_spawn_agent
from sub_agent_mcp.config.schema import AgentConfig, AgentsFile
from sub_agent_mcp.logging import get_logger
from sub_agent_mcp.server.openapi import register_openapi_route

logger = get_logger(__name__)


def _agent_tool_description(agent: AgentConfig) -> str:
    return f"{agent.title}: {agent.description} (model: {agent.llm.model_id})"


def register_tools(mcp: FastMCP, config: AgentsFile) -> None:
    """Register one MCP tool per agent defined in config."""

    for agent in config.agents:

        def make_tool(agent_config: AgentConfig) -> None:
            @mcp.tool(
                name=agent_config.id,
                description=_agent_tool_description(agent_config),
            )
            async def agent_tool(prompt: str) -> dict[str, str]:
                """Run this sub-agent with the given prompt."""
                try:
                    response = await run_spawn_agent(config, agent_config.id, prompt)
                    return {"response": response}
                except AgentNotFoundError as exc:
                    return {"error": str(exc)}
                except AgentError as exc:
                    logger.error(
                        "agent_tool_error",
                        agent_id=agent_config.id,
                        error=str(exc),
                    )
                    return {"error": str(exc)}

        make_tool(agent)

    register_openapi_route(mcp)
