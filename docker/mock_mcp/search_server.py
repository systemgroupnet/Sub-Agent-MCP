"""Mock search MCP server for development."""

from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    "SearchMCP",
    host="0.0.0.0",
    port=8002,
    stateless_http=True,
    json_response=True,
)


@mcp.tool()
def web_search(query: str) -> str:
    """Search the web for information."""
    return f"Search results for: {query}"


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
