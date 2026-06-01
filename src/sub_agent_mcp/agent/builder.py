"""Build LangChain agents from agent configuration."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

from sub_agent_mcp.config.schema import AgentConfig
from sub_agent_mcp.logging import get_logger
from sub_agent_mcp.mcp_client.manager import get_langchain_tools

if TYPE_CHECKING:
    from langchain_openai import ChatOpenAI

logger = get_logger(__name__)

DEFAULT_RECURSION_LIMIT = int(os.getenv("AGENT_RECURSION_LIMIT", "25"))


def build_llm(agent: AgentConfig) -> ChatOpenAI:
    """Create an OpenAI-compatible chat model from agent LLM config."""
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=agent.llm.model_id,
        base_url=str(agent.llm.base_uri),
        api_key=agent.llm.api_key.get_secret_value(),
    )


async def build_agent(agent: AgentConfig) -> Any:
    """Build a LangChain agent with MCP tools for the given agent config."""
    from langchain.agents import create_agent

    model = build_llm(agent)
    tools = await get_langchain_tools(agent)

    if agent.mcp_servers and not tools:
        logger.warning(
            "agent_no_tools_after_filter",
            agent_id=agent.id,
            allowlist=agent.tool_allowlist,
        )

    return create_agent(
        model,
        tools=tools,
        system_prompt=agent.system_prompt,
    )


def get_recursion_limit() -> int:
    """Return the configured agent recursion limit."""
    return DEFAULT_RECURSION_LIMIT
