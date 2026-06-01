"""Mock filesystem MCP server for development."""

from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    "FilesystemMCP",
    host="0.0.0.0",
    port=8001,
    stateless_http=True,
    json_response=True,
)


@mcp.tool()
def read_file(path: str) -> str:
    """Read a file from disk."""
    return f"Contents of {path}"


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
