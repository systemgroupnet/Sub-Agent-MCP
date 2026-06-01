"""Tests for list_agents MCP tool behavior."""

from __future__ import annotations

import json

import pytest

from sub_agent_mcp.config.schema import AgentsFile
from sub_agent_mcp.mcp_client.tool_registry import discover_tools


@pytest.mark.asyncio
async def test_list_agents_output_sanitized(agents_config: AgentsFile) -> None:
    """Simulate list_agents output and verify no secrets are exposed."""
    agents_output = []

    for agent in agents_config.agents:
        tools = await discover_tools(agent)
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

    serialized = json.dumps(agents_output)

    assert "test-key" not in serialized
    assert "api_key" not in serialized
    assert agents_output[0]["id"] == "researcher"
    assert agents_output[0]["model_id"] == "gpt-4.1-mini"
    assert len(agents_output[0]["available_tools"]) == 2
