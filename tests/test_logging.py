"""Tests for agent execution logging."""

from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
import structlog
from structlog.testing import LogCapture

import sub_agent_mcp.agent.executor as executor_module
from sub_agent_mcp.agent.errors import AgentExecutionError
from sub_agent_mcp.agent.executor import spawn_agent
from sub_agent_mcp.config.schema import AgentsFile
from sub_agent_mcp.logging import get_logger


@contextmanager
def capture_agent_logs() -> Iterator[list[dict[str, object]]]:
    """Capture structlog events including contextvars-bound fields."""
    cap = LogCapture()
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            cap,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=False,
    )
    executor_module.logger = get_logger(executor_module.__name__)
    try:
        yield cap.entries
    finally:
        structlog.reset_defaults()


def _events_by_name(logs: list[dict[str, object]]) -> dict[str, list[dict[str, object]]]:
    grouped: dict[str, list[dict[str, object]]] = {}
    for entry in logs:
        event = entry["event"]
        assert isinstance(event, str)
        grouped.setdefault(event, []).append(entry)
    return grouped


@pytest.mark.asyncio
async def test_spawn_agent_success_logs_trace_model_and_io(agents_config: AgentsFile) -> None:
    mock_runnable = AsyncMock()
    mock_runnable.ainvoke.return_value = {
        "messages": [SimpleNamespace(content="Research complete.")]
    }
    prompt = "Find info on MCP"

    with (
        patch("sub_agent_mcp.agent.executor.build_agent", return_value=mock_runnable),
        capture_agent_logs() as logs,
    ):
        response = await spawn_agent(agents_config, "researcher", prompt)

    assert response == "Research complete."

    events = _events_by_name(logs)
    trace_ids = {entry["trace_id"] for entry in logs if "trace_id" in entry}
    assert len(trace_ids) == 1

    trace_id = trace_ids.pop()
    start_logs = events["spawn_agent_start"]
    assert start_logs[0]["model_id"] == "gpt-4.1-mini"
    assert start_logs[0]["agent_id"] == "researcher"
    assert start_logs[0]["trace_id"] == trace_id

    input_logs = events["agent_input"]
    assert input_logs[0]["input"] == prompt
    assert input_logs[0]["trace_id"] == trace_id

    output_logs = events["agent_output"]
    assert output_logs[0]["output"] == "Research complete."
    assert output_logs[0]["trace_id"] == trace_id

    complete_logs = events["spawn_agent_complete"]
    assert complete_logs[0]["trace_id"] == trace_id


@pytest.mark.asyncio
async def test_spawn_agent_auth_error_logs_input_with_trace_id(agents_config: AgentsFile) -> None:
    mock_runnable = AsyncMock()
    mock_runnable.ainvoke.side_effect = Exception("401 Unauthorized")
    prompt = "Hello"

    with (
        patch("sub_agent_mcp.agent.executor.build_agent", return_value=mock_runnable),
        capture_agent_logs() as logs,
        pytest.raises(AgentExecutionError, match="Invalid credentials"),
    ):
        await spawn_agent(agents_config, "researcher", prompt)

    events = _events_by_name(logs)
    trace_ids = {entry["trace_id"] for entry in logs if "trace_id" in entry}
    assert len(trace_ids) == 1
    trace_id = trace_ids.pop()

    input_logs = events["agent_input"]
    assert input_logs[0]["input"] == prompt
    assert input_logs[0]["trace_id"] == trace_id

    error_logs = events["agent_auth_failed"]
    assert error_logs[0]["trace_id"] == trace_id
    assert error_logs[0]["model_id"] == "gpt-4.1-mini"

    assert "agent_output" not in events
