"""Execute sub-agent prompts."""

from __future__ import annotations

from sub_agent_mcp.agent.builder import build_agent, get_recursion_limit
from sub_agent_mcp.agent.errors import AgentExecutionError, AgentNotFoundError
from sub_agent_mcp.config.schema import AgentConfig, AgentsFile
from sub_agent_mcp.logging import get_logger

logger = get_logger(__name__)


async def spawn_agent(config: AgentsFile, agent_id: str, prompt: str) -> str:
    """Run a sub-agent with the given prompt and return the final response."""
    agent = config.get_agent(agent_id)
    if agent is None:
        raise AgentNotFoundError(f"Agent not found: {agent_id}")

    return await execute_agent(agent, prompt)


async def execute_agent(agent: AgentConfig, prompt: str) -> str:
    """Build and run a single agent, returning the final assistant message."""
    from langchain_core.messages import HumanMessage
    from openai import AuthenticationError, OpenAIError

    logger.info("spawn_agent_start", agent_id=agent.id)

    try:
        runnable = await build_agent(agent)
        result = await runnable.ainvoke(
            {"messages": [HumanMessage(content=prompt)]},
            config={"recursion_limit": get_recursion_limit()},
        )
    except AuthenticationError as exc:
        logger.error("agent_auth_failed", agent_id=agent.id)
        raise AgentExecutionError(
            f"Invalid credentials for agent '{agent.id}' LLM provider"
        ) from exc
    except OpenAIError as exc:
        logger.error("agent_llm_error", agent_id=agent.id, error=str(exc))
        raise AgentExecutionError(f"LLM error for agent '{agent.id}': {exc}") from exc
    except Exception as exc:
        if "401" in str(exc) or "authentication" in str(exc).lower():
            logger.error("agent_auth_failed", agent_id=agent.id)
            raise AgentExecutionError(
                f"Invalid credentials for agent '{agent.id}' LLM provider"
            ) from exc
        logger.error("agent_execution_failed", agent_id=agent.id, error=str(exc))
        raise AgentExecutionError(f"Agent execution failed for '{agent.id}': {exc}") from exc

    messages = result.get("messages", [])
    if not messages:
        raise AgentExecutionError(f"Agent '{agent.id}' returned no messages")

    final_message = messages[-1]
    content = getattr(final_message, "content", None)
    if content is None:
        raise AgentExecutionError(f"Agent '{agent.id}' returned empty content")

    if isinstance(content, list):
        text_parts = [
            part.get("text", "")
            for part in content
            if isinstance(part, dict) and part.get("type") == "text"
        ]
        response = "\n".join(part for part in text_parts if part)
    else:
        response = str(content)

    logger.info("spawn_agent_complete", agent_id=agent.id)
    return response
