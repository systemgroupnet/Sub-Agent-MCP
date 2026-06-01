"""Agent execution exceptions."""

from __future__ import annotations


class AgentError(Exception):
    """Base exception for agent errors."""


class AgentNotFoundError(AgentError):
    """Raised when the requested agent id does not exist."""


class MCPConnectionError(AgentError):
    """Raised when an MCP server cannot be reached."""


class AgentExecutionError(AgentError):
    """Raised when agent execution fails."""
