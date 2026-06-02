"""Tests for per-agent MCP tool registration."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from sub_agent_mcp.config.schema import AgentsFile
from sub_agent_mcp.main import create_app


@pytest.fixture
def mcp_app(agents_config: AgentsFile):
    """Create FastMCP app with test config."""
    with patch("sub_agent_mcp.main.load_agents_config", return_value=agents_config):
        mcp = create_app()
    return mcp


def test_one_tool_registered_per_agent(mcp_app: object) -> None:
    tools = mcp_app._tool_manager.list_tools()  # type: ignore[attr-defined]
    tool_names = {tool.name for tool in tools}

    assert tool_names == {"researcher"}


def test_agent_tool_descriptions_exclude_secrets(mcp_app: object) -> None:
    tools = mcp_app._tool_manager.list_tools()  # type: ignore[attr-defined]
    serialized = json.dumps(
        [
            {
                "name": tool.name,
                "description": tool.description,
            }
            for tool in tools
        ]
    )

    assert "test-key" not in serialized
    assert "api_key" not in serialized
    assert "researcher" in serialized
    assert "gpt-4.1-mini" in serialized
