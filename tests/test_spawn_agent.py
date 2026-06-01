"""Tests for spawn_agent execution flow."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from langchain_core.messages import AIMessage

from sub_agent_mcp.agent.errors import AgentExecutionError, AgentNotFoundError
from sub_agent_mcp.agent.executor import spawn_agent
from sub_agent_mcp.config.schema import AgentsFile


@pytest.mark.asyncio
async def test_spawn_agent_not_found(agents_config: AgentsFile) -> None:
    with pytest.raises(AgentNotFoundError, match="missing-agent"):
        await spawn_agent(agents_config, "missing-agent", "Hello")


@pytest.mark.asyncio
async def test_spawn_agent_success(agents_config: AgentsFile) -> None:
    mock_runnable = AsyncMock()
    mock_runnable.ainvoke.return_value = {
        "messages": [AIMessage(content="Research complete.")]
    }

    with patch("sub_agent_mcp.agent.executor.build_agent", return_value=mock_runnable):
        response = await spawn_agent(agents_config, "researcher", "Find info on MCP")

    assert response == "Research complete."
    mock_runnable.ainvoke.assert_awaited_once()


@pytest.mark.asyncio
async def test_spawn_agent_auth_error(agents_config: AgentsFile) -> None:
    mock_runnable = AsyncMock()
    mock_runnable.ainvoke.side_effect = Exception("401 Unauthorized")

    with (
        patch("sub_agent_mcp.agent.executor.build_agent", return_value=mock_runnable),
        pytest.raises(AgentExecutionError, match="Invalid credentials"),
    ):
        await spawn_agent(agents_config, "researcher", "Hello")


@pytest.mark.asyncio
async def test_spawn_agent_empty_response(agents_config: AgentsFile) -> None:
    mock_runnable = AsyncMock()
    mock_runnable.ainvoke.return_value = {"messages": []}

    with (
        patch("sub_agent_mcp.agent.executor.build_agent", return_value=mock_runnable),
        pytest.raises(AgentExecutionError, match="returned no messages"),
    ):
        await spawn_agent(agents_config, "researcher", "Hello")
