"""OpenAPI document generation and REST tool routes for Open WebUI."""

from __future__ import annotations

import json
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from mcp.server.fastmcp.tools.base import Tool
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from sub_agent_mcp import __version__

OPENAPI_PATH = "/mcp/openapi.json"
MCP_TRANSPORT_PATH = "/mcp"
# Open WebUI appends these paths to the configured server URL (typically .../mcp).
OPENAPI_TOOLS_PATH_PREFIX = "/tools"
# Also serve legacy paths when the server URL is the reverse-proxy mount (e.g. .../sub-agent).
HTTP_TOOL_ROUTE_PREFIXES = (OPENAPI_TOOLS_PATH_PREFIX, "/mcp/tools")


def _tool_request_schema(tool: Tool) -> dict[str, Any]:
    """Build request body schema for a tool operation."""
    properties = dict(tool.parameters.get("properties", {}))
    required = list(tool.parameters.get("required", []))
    return {
        "type": "object",
        "properties": properties,
        "required": required,
    }


def _tool_response_schema(tool: Tool) -> dict[str, Any]:
    """Build response schema for a tool operation."""
    if tool.output_schema is not None:
        return tool.output_schema
    return {
        "type": "object",
        "description": "Tool result (unstructured)",
    }


def build_openapi_document(mcp: FastMCP) -> dict[str, Any]:
    """Generate an OpenAPI 3.1 document from registered FastMCP tools."""
    paths: dict[str, Any] = {
        MCP_TRANSPORT_PATH: {
            "post": {
                "operationId": "mcpStreamableHttp",
                "summary": "MCP Streamable HTTP transport",
                "description": (
                    "Primary MCP endpoint (JSON-RPC over Streamable HTTP). "
                    "Use an MCP client to call agent tools registered from agents.yaml."
                ),
                "tags": ["mcp"],
                "responses": {
                    "200": {"description": "MCP response"},
                    "406": {"description": "Not acceptable (wrong Accept header)"},
                },
            },
            "get": {
                "operationId": "mcpStreamableHttpSse",
                "summary": "MCP Streamable HTTP SSE stream",
                "tags": ["mcp"],
                "responses": {"200": {"description": "Server-sent events stream"}},
            },
            "delete": {
                "operationId": "mcpStreamableHttpTerminate",
                "summary": "Terminate MCP session",
                "tags": ["mcp"],
                "responses": {"200": {"description": "Session terminated"}},
            },
        },
        OPENAPI_PATH: {
            "get": {
                "operationId": "getOpenApi",
                "summary": "OpenAPI specification",
                "tags": ["meta"],
                "responses": {
                    "200": {
                        "description": "OpenAPI 3.1 document",
                        "content": {"application/json": {"schema": {"type": "object"}}},
                    }
                },
            }
        },
    }

    for tool in mcp._tool_manager.list_tools():
        path = f"{OPENAPI_TOOLS_PATH_PREFIX}/{tool.name}"
        paths[path] = {
            "post": {
                "operationId": tool.name,
                "summary": tool.title or tool.name,
                "description": tool.description,
                "tags": ["tools"],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": _tool_request_schema(tool),
                        }
                    },
                },
                "responses": {
                    "200": {
                        "description": "Tool result",
                        "content": {
                            "application/json": {
                                "schema": _tool_response_schema(tool),
                            }
                        },
                    }
                },
            }
        }

    return {
        "openapi": "3.1.0",
        "info": {
            "title": mcp.name,
            "version": __version__,
            "description": (
                "Sub-Agent MCP server. Each agent in agents.yaml is exposed as a tool. "
                "Invoke via MCP JSON-RPC at "
                f"{MCP_TRANSPORT_PATH} or via OpenAPI-compatible POST requests at "
                f"{OPENAPI_TOOLS_PATH_PREFIX}/{{agent_id}}."
            ),
        },
        "paths": paths,
        "tags": [
            {"name": "mcp", "description": "Model Context Protocol transport"},
            {"name": "tools", "description": "OpenAPI-compatible REST tool endpoints"},
            {"name": "meta", "description": "Server metadata"},
        ],
    }


def _tool_http_response(result: Any) -> dict[str, Any]:
    """Normalize FastMCP tool output for Open WebUI OpenAPI clients."""
    if isinstance(result, tuple) and len(result) == 2:
        structured = result[1]
        if isinstance(structured, dict):
            return structured
    if isinstance(result, dict):
        return result
    if isinstance(result, list):
        return {"result": result}
    return {"result": result}


def register_tool_http_routes(mcp: FastMCP) -> None:
    """Register OpenAPI-compatible POST tool routes for Open WebUI."""

    for tool in mcp._tool_manager.list_tools():
        def make_handler(tool_name: str):
            async def tool_handler(request: Request) -> Response:
                try:
                    body = await request.json()
                except json.JSONDecodeError:
                    return JSONResponse(
                        {"error": "Request body must be valid JSON"},
                        status_code=400,
                    )

                if body is None:
                    body = {}
                if not isinstance(body, dict):
                    return JSONResponse(
                        {"error": "Request body must be a JSON object"},
                        status_code=400,
                    )

                try:
                    result = await mcp.call_tool(tool_name, body)
                except ToolError as exc:
                    return JSONResponse({"error": str(exc)}, status_code=500)

                return JSONResponse(_tool_http_response(result))

            return tool_handler

        handler = make_handler(tool.name)
        for prefix in HTTP_TOOL_ROUTE_PREFIXES:
            path = f"{prefix}/{tool.name}"
            route_name = f"tool_{tool.name}_{prefix.strip('/').replace('/', '_')}"
            mcp.custom_route(path, methods=["POST"], name=route_name)(handler)


def register_openapi_route(mcp: FastMCP) -> None:
    """Register OpenAPI metadata and REST tool routes on the FastMCP HTTP app."""
    register_tool_http_routes(mcp)

    @mcp.custom_route(OPENAPI_PATH, methods=["GET"], name="openapi")
    async def openapi_handler(_request: Request) -> Response:
        document = build_openapi_document(mcp)
        return JSONResponse(document)
