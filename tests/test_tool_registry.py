"""Tests for tool registry filtering and validation."""

from __future__ import annotations

import pytest

from sub_agent_mcp.config.schema import AgentConfig, LLMConfig, MCPServerConfig
from sub_agent_mcp.mcp_client.manager import get_langchain_tools
from sub_agent_mcp.mcp_client.tool_registry import (
    allows_all_tools,
    discover_tools,
    is_tool_allowed,
    qualified_tool_name,
    validate_tool_schema,
)


def test_qualified_tool_name() -> None:
    assert qualified_tool_name("filesystem", "read_file") == "filesystem.read_file"


def test_is_tool_allowed_none_allowlist() -> None:
    assert allows_all_tools(None) is True
    assert is_tool_allowed("filesystem", "read_file", None) is True


def test_is_tool_allowed_with_allowlist() -> None:
    assert allows_all_tools(["filesystem.read_file"]) is False
    allowlist = ["filesystem.read_file"]
    assert is_tool_allowed("filesystem", "read_file", allowlist) is True
    assert is_tool_allowed("filesystem", "write_file", allowlist) is False


@pytest.mark.parametrize(
    ("name", "description", "schema", "expected"),
    [
        ("read_file", "Read a file", None, True),
        ("read_file", "Read a file", {"type": "object", "properties": {}}, True),
        ("", "Read a file", None, False),
        ("read_file", "", None, False),
        ("read_file", "Read a file", "invalid", False),
        ("read_file", "Read a file", {"type": "string"}, False),
        ("read_file", "Read a file", {"type": "object", "properties": "bad"}, False),
    ],
)
def test_validate_tool_schema(
    name: str,
    description: str | None,
    schema: object,
    expected: bool,
) -> None:
    assert validate_tool_schema(name, description, schema) is expected  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_discover_tools_with_allowlist(agents_config: object) -> None:
    tools = await discover_tools(agents_config.agents[0])  # type: ignore[attr-defined]

    qualified = {tool.qualified_name for tool in tools}
    assert "filesystem.read_file" in qualified
    assert "search.web_search" in qualified
    assert len(tools) == 2


@pytest.mark.asyncio
async def test_discover_tools_all_when_no_allowlist(mock_mcp_servers: tuple[int, int]) -> None:
    fs_port, search_port = mock_mcp_servers
    agent = AgentConfig(
        id="researcher",
        title="Research Agent",
        description="Test agent",
        llm=LLMConfig(
            base_uri="https://api.openai.com/v1",
            api_key="test-key",
            model_id="gpt-4.1-mini",
        ),
        system_prompt="Test prompt",
        mcp_servers=[
            MCPServerConfig(
                name="filesystem",
                transport="streamable_http",
                url=f"http://127.0.0.1:{fs_port}/mcp",
            ),
            MCPServerConfig(
                name="search",
                transport="streamable_http",
                url=f"http://127.0.0.1:{search_port}/mcp",
            ),
        ],
        tool_allowlist=None,
    )

    tools = await discover_tools(agent)
    assert len(tools) == 2


@pytest.mark.asyncio
async def test_get_langchain_tools_without_allowlist(mock_mcp_servers: tuple[int, int]) -> None:
    fs_port, search_port = mock_mcp_servers
    agent = AgentConfig(
        id="researcher",
        title="Research Agent",
        description="Test agent",
        llm=LLMConfig(
            base_uri="https://api.openai.com/v1",
            api_key="test-key",
            model_id="gpt-4.1-mini",
        ),
        system_prompt="Test prompt",
        mcp_servers=[
            MCPServerConfig(
                name="filesystem",
                transport="streamable_http",
                url=f"http://127.0.0.1:{fs_port}/mcp",
            ),
            MCPServerConfig(
                name="search",
                transport="streamable_http",
                url=f"http://127.0.0.1:{search_port}/mcp",
            ),
        ],
    )

    tools = await get_langchain_tools(agent)

    assert len(tools) == 2
    tool_names = {tool.name for tool in tools}
    assert tool_names == {"read_file", "web_search"}
