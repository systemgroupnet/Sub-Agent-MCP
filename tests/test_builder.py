"""Tests for LangChain LLM builder kwargs."""

from __future__ import annotations

from pydantic import SecretStr

from sub_agent_mcp.agent.builder import build_llm_kwargs
from sub_agent_mcp.config.schema import AgentConfig, LLMConfig


def _agent(**llm_overrides: object) -> AgentConfig:
    llm_data = {
        "base_uri": "https://openrouter.ai/api/v1",
        "api_key": SecretStr("test-key"),
        "model_id": "openai/gpt-5.4",
    }
    llm_data.update(llm_overrides)
    return AgentConfig(
        id="researcher",
        title="Research Agent",
        description="Test agent",
        llm=LLMConfig(**llm_data),
        system_prompt="You are helpful.",
    )


def test_build_llm_kwargs_minimal() -> None:
    kwargs = build_llm_kwargs(_agent())

    assert kwargs == {
        "model": "openai/gpt-5.4",
        "base_url": "https://openrouter.ai/api/v1",
        "api_key": "test-key",
    }


def test_build_llm_kwargs_includes_reasoning_effort() -> None:
    kwargs = build_llm_kwargs(_agent(reasoning_effort="high"))

    assert kwargs["reasoning_effort"] == "high"
    assert kwargs["reasoning"] == {"effort": "high"}
    assert kwargs["extra_body"] == {"reasoning": {"effort": "high"}}


def test_build_llm_kwargs_includes_reasoning_summary() -> None:
    kwargs = build_llm_kwargs(
        _agent(
            reasoning_effort="medium",
            reasoning_summary="detailed",
            max_tokens=8192,
            verbosity="high",
        )
    )

    assert kwargs["max_tokens"] == 8192
    assert kwargs["verbosity"] == "high"
    assert kwargs["extra_body"] == {
        "reasoning": {"effort": "medium", "summary": "detailed"},
    }
