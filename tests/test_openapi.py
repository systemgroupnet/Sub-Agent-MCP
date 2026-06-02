"""Tests for OpenAPI document generation and route."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

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


def test_build_openapi_document_includes_agent_tools(mcp_app: object) -> None:
    document = build_openapi_document(mcp_app)  # type: ignore[arg-type]

    assert document["openapi"] == "3.1.0"
    assert document["info"]["title"] == "SubAgentMCP"

    paths = document["paths"]
    assert OPENAPI_PATH in paths
    assert "/tools/researcher" in paths

    researcher = paths["/tools/researcher"]["post"]
    props = researcher["requestBody"]["content"]["application/json"]["schema"]["properties"]
    assert "prompt" in props
    assert researcher["operationId"] == "researcher"


def test_openapi_route_returns_json(mcp_app: object) -> None:
    app = mcp_app.streamable_http_app()  # type: ignore[attr-defined]
    with TestClient(app) as client:
        response = client.get(OPENAPI_PATH)

    assert response.status_code == 200
    document = json.loads(response.text)
    assert document["paths"]["/tools/researcher"]["post"]["operationId"] == "researcher"


def test_researcher_http_route(mcp_app: object) -> None:
    app = mcp_app.streamable_http_app()  # type: ignore[attr-defined]
    mock_runnable = AsyncMock()
    mock_runnable.ainvoke.return_value = {
        "messages": [type("Msg", (), {"content": "Done."})()],
    }

    with patch("sub_agent_mcp.agent.executor.build_agent", return_value=mock_runnable):
        with TestClient(app) as client:
            response = client.post(
                "/tools/researcher",
                json={"prompt": "Hello"},
            )

    assert response.status_code == 200
    assert response.json() == {"response": "Done."}


def test_researcher_legacy_http_route(mcp_app: object) -> None:
    app = mcp_app.streamable_http_app()  # type: ignore[attr-defined]
    mock_runnable = AsyncMock()
    mock_runnable.ainvoke.return_value = {
        "messages": [type("Msg", (), {"content": "Done."})()],
    }

    with patch("sub_agent_mcp.agent.executor.build_agent", return_value=mock_runnable):
        with TestClient(app) as client:
            response = client.post(
                "/mcp/tools/researcher",
                json={"prompt": "Hello"},
            )

    assert response.status_code == 200
    assert response.json() == {"response": "Done."}


def test_researcher_http_route_missing_prompt(mcp_app: object) -> None:
    app = mcp_app.streamable_http_app()  # type: ignore[attr-defined]
    with TestClient(app) as client:
        response = client.post("/tools/researcher", json={})

    assert response.status_code == 500
    assert "error" in response.json()
