"""Shared pytest fixtures."""

from __future__ import annotations

import asyncio
import contextlib
import socket
import threading
import time
from collections.abc import Iterator
from pathlib import Path

import pytest
import uvicorn
from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.routing import Mount

from sub_agent_mcp.config.schema import AgentConfig, AgentsFile, LLMConfig, MCPServerConfig


def find_free_port() -> int:
    """Return an ephemeral TCP port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def create_mock_mcp_server(tools: dict[str, str]) -> FastMCP:
    """Create a FastMCP server with stub tools."""
    server = FastMCP(
        "MockMCP",
        host="127.0.0.1",
        stateless_http=True,
        json_response=True,
    )

    for tool_name, description in tools.items():

        def make_tool(name: str, desc: str) -> None:
            @server.tool(name=name, description=desc)
            def tool_impl(value: str = "") -> str:
                return f"{name}:{value}"

        make_tool(tool_name, description)

    return server


def start_server(server: FastMCP, port: int) -> threading.Thread:
    """Start a FastMCP server in a background thread."""
    @contextlib.asynccontextmanager
    async def lifespan(app: Starlette):
        async with server.session_manager.run():
            yield

    app = Starlette(
        routes=[Mount("/", app=server.streamable_http_app())],
        lifespan=lifespan,
    )
    config = uvicorn.Config(
        app,
        host="127.0.0.1",
        port=port,
        log_level="error",
        ws="none",
    )
    uvicorn_server = uvicorn.Server(config)

    thread = threading.Thread(target=asyncio.run, args=(uvicorn_server.serve(),), daemon=True)
    thread.start()
    return thread


def wait_for_server(port: int, timeout: float = 5.0) -> None:
    """Wait until a TCP port accepts connections."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.2)
            if sock.connect_ex(("127.0.0.1", port)) == 0:
                return
        time.sleep(0.05)
    msg = f"Mock MCP server did not start on port {port}"
    raise RuntimeError(msg)


@pytest.fixture
def mock_mcp_servers() -> Iterator[tuple[int, int]]:
    """Start filesystem and search mock MCP servers."""
    fs_port = find_free_port()
    search_port = find_free_port()

    fs_server = create_mock_mcp_server({"read_file": "Read a file from disk"})
    search_server = create_mock_mcp_server({"web_search": "Search the web"})

    start_server(fs_server, fs_port)
    start_server(search_server, search_port)
    wait_for_server(fs_port)
    wait_for_server(search_port)

    yield fs_port, search_port


@pytest.fixture
def agents_config(mock_mcp_servers: tuple[int, int]) -> AgentsFile:
    """Build a test AgentsFile wired to mock MCP servers."""
    fs_port, search_port = mock_mcp_servers
    return AgentsFile(
        agents=[
            AgentConfig(
                id="researcher",
                title="Research Agent",
                description="Agent specialized in research tasks",
                llm=LLMConfig(
                    base_uri="https://api.openai.com/v1",
                    api_key="test-key",
                    model_id="gpt-4.1-mini",
                ),
                system_prompt="You are a helpful research assistant.",
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
                tool_allowlist=[
                    "filesystem.read_file",
                    "search.web_search",
                ],
            )
        ]
    )


@pytest.fixture
def agents_yaml(tmp_path: Path, mock_mcp_servers: tuple[int, int]) -> Path:
    """Write a temporary agents.yaml for integration tests."""
    fs_port, search_port = mock_mcp_servers
    config_path = tmp_path / "agents.yaml"
    config_path.write_text(
        f"""
agents:
  - id: researcher
    title: Research Agent
    description: "Agent specialized in research tasks"
    llm:
      base_uri: https://api.openai.com/v1
      api_key: test-key
      model_id: gpt-4.1-mini
    system_prompt: |
      You are a helpful research assistant.
    mcp_servers:
      - name: filesystem
        transport: streamable_http
        url: http://127.0.0.1:{fs_port}/mcp
      - name: search
        transport: streamable_http
        url: http://127.0.0.1:{search_port}/mcp
    tool_allowlist:
      - filesystem.read_file
      - search.web_search
""",
        encoding="utf-8",
    )
    return config_path
