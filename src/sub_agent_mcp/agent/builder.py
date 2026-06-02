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


def build_llm_kwargs(agent: AgentConfig) -> dict[str, Any]:
    """Map agent LLM config to ChatOpenAI constructor kwargs."""
    llm = agent.llm
    kwargs: dict[str, Any] = {
        "model": llm.model_id,
        "base_url": str(llm.base_uri),
        "api_key": llm.api_key.get_secret_value(),
    }

    for field in ("temperature", "max_tokens", "verbosity"):
        value = getattr(llm, field)
        if value is not None:
            kwargs[field] = value

    reasoning: dict[str, str] = {}
    if llm.reasoning_effort is not None:
        reasoning["effort"] = llm.reasoning_effort
        kwargs["reasoning_effort"] = llm.reasoning_effort
    if llm.reasoning_summary is not None:
        reasoning["summary"] = llm.reasoning_summary

    if reasoning:
        kwargs["reasoning"] = reasoning
        # OpenRouter and other OpenAI-compatible providers expect reasoning here.
        kwargs["extra_body"] = {"reasoning": reasoning}

    return kwargs


def build_llm(agent: AgentConfig) -> ChatOpenAI:
    """Create an OpenAI-compatible chat model from agent LLM config."""
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(**build_llm_kwargs(agent))


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
