"""Tests for OpenAPI document generation and route."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest
from starlette.testclient import TestClient

from sub_agent_mcp.config.schema import AgentsFile
from sub_agent_mcp.main import create_app
from sub_agent_mcp.server.openapi import OPENAPI_PATH, build_openapi_document


@pytest.fixture
def mcp_app(agents_config: AgentsFile):
    """Create FastMCP app with test config."""
    with patch("sub_agent_mcp.main.load_agents_config", return_value=agents_config):
        mcp = create_app()
    return mcp


def test_build_openapi_document_includes_tools(mcp_app: object) -> None:
    document = build_openapi_document(mcp_app)  # type: ignore[arg-type]

    assert document["openapi"] == "3.1.0"
    assert document["info"]["title"] == "SubAgentMCP"

    paths = document["paths"]
    assert OPENAPI_PATH in paths
    assert "/mcp/tools/list_agents" in paths
    assert "/mcp/tools/spawn_agent" in paths

    spawn = paths["/mcp/tools/spawn_agent"]["post"]
    props = spawn["requestBody"]["content"]["application/json"]["schema"]["properties"]
    assert "agent_id" in props
    assert "prompt" in props


def test_openapi_route_returns_json(mcp_app: object) -> None:
    app = mcp_app.streamable_http_app()  # type: ignore[attr-defined]
    with TestClient(app) as client:
        response = client.get(OPENAPI_PATH)

    assert response.status_code == 200
    document = json.loads(response.text)
    assert document["paths"]["/mcp/tools/list_agents"]["post"]["operationId"] == "list_agents"


def test_list_agents_http_route(mcp_app: object) -> None:
    app = mcp_app.streamable_http_app()  # type: ignore[attr-defined]
    with TestClient(app) as client:
        response = client.post("/mcp/tools/list_agents", json={})

    assert response.status_code == 200
    payload = response.json()
    assert "result" in payload
    assert payload["result"][0]["id"] == "researcher"


def test_spawn_agent_http_route_missing_args(mcp_app: object) -> None:
    app = mcp_app.streamable_http_app()  # type: ignore[attr-defined]
    with TestClient(app) as client:
        response = client.post("/mcp/tools/spawn_agent", json={})

    assert response.status_code == 500
    assert "error" in response.json()
