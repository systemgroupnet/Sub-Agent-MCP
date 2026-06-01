"""Tests for configuration loading and validation."""

from __future__ import annotations

from pathlib import Path

import pytest

from sub_agent_mcp.config.errors import (
    ConfigFileNotFoundError,
    ConfigValidationError,
    EnvVarNotFoundError,
)
from sub_agent_mcp.config.loader import load_agents_config, substitute_env_vars
from sub_agent_mcp.config.schema import AgentsFile

VALID_YAML = """
agents:
  - id: researcher
    title: Research Agent
    description: "Agent specialized in research tasks"
    llm:
      base_uri: https://api.openai.com/v1
      api_key: sk-test-key
      model_id: gpt-4.1-mini
    system_prompt: |
      You are a helpful research assistant.
    mcp_servers:
      - name: filesystem
        transport: streamable_http
        url: http://filesystem-mcp:8001/mcp
    tool_allowlist:
      - filesystem.read_file
"""


def test_substitute_env_vars_with_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "secret-key")
    result = substitute_env_vars("key: ${OPENAI_API_KEY}")
    assert result == "key: secret-key"


def test_substitute_env_vars_with_default() -> None:
    result = substitute_env_vars("key: ${MISSING_VAR:-fallback}")
    assert result == "key: fallback"


def test_substitute_env_vars_missing_required(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("REQUIRED_VAR", raising=False)
    with pytest.raises(EnvVarNotFoundError, match="REQUIRED_VAR"):
        substitute_env_vars("key: ${REQUIRED_VAR}")


def test_load_valid_config(tmp_path: Path) -> None:
    config_file = tmp_path / "agents.yaml"
    config_file.write_text(VALID_YAML, encoding="utf-8")

    config = load_agents_config(config_file)

    assert isinstance(config, AgentsFile)
    assert len(config.agents) == 1
    assert config.agents[0].id == "researcher"
    assert config.agents[0].llm.model_id == "gpt-4.1-mini"


def test_load_config_with_env_substitution(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_file = tmp_path / "agents.yaml"
    config_file.write_text(
        VALID_YAML.replace("sk-test-key", "${OPENAI_API_KEY}"),
        encoding="utf-8",
    )
    monkeypatch.setenv("OPENAI_API_KEY", "env-secret")

    config = load_agents_config(config_file)

    assert config.agents[0].llm.api_key.get_secret_value() == "env-secret"


def test_load_missing_config_file(tmp_path: Path) -> None:
    with pytest.raises(ConfigFileNotFoundError):
        load_agents_config(tmp_path / "missing.yaml")


def test_load_invalid_yaml(tmp_path: Path) -> None:
    config_file = tmp_path / "agents.yaml"
    config_file.write_text("agents: [invalid", encoding="utf-8")

    with pytest.raises(ConfigValidationError, match="Invalid YAML"):
        load_agents_config(config_file)


def test_duplicate_agent_ids(tmp_path: Path) -> None:
    config_file = tmp_path / "agents.yaml"
    config_file.write_text(
        VALID_YAML
        + """
  - id: researcher
    title: Duplicate
    description: Duplicate agent
    llm:
      base_uri: https://api.openai.com/v1
      api_key: sk-test
      model_id: gpt-4.1-mini
    system_prompt: Duplicate
""",
        encoding="utf-8",
    )

    with pytest.raises(ConfigValidationError, match="Duplicate agent ids"):
        load_agents_config(config_file)


def test_invalid_transport(tmp_path: Path) -> None:
    config_file = tmp_path / "agents.yaml"
    config_file.write_text(
        VALID_YAML.replace("streamable_http", "stdio"),
        encoding="utf-8",
    )

    with pytest.raises(ConfigValidationError, match="Config validation failed"):
        load_agents_config(config_file)


def test_invalid_agent_id(tmp_path: Path) -> None:
    config_file = tmp_path / "agents.yaml"
    config_file.write_text(
        VALID_YAML.replace("id: researcher", "id: Invalid-ID"),
        encoding="utf-8",
    )

    with pytest.raises(ConfigValidationError, match="Config validation failed"):
        load_agents_config(config_file)


def test_load_config_without_tool_allowlist(tmp_path: Path) -> None:
    """Omitting tool_allowlist from YAML allows all tools."""
    yaml_without_allowlist = """
agents:
  - id: researcher
    title: Research Agent
    description: "Agent specialized in research tasks"
    llm:
      base_uri: https://api.openai.com/v1
      api_key: sk-test-key
      model_id: gpt-4.1-mini
    system_prompt: |
      You are a helpful research assistant.
    mcp_servers:
      - name: filesystem
        transport: streamable_http
        url: http://filesystem-mcp:8001/mcp
"""
    config_file = tmp_path / "agents.yaml"
    config_file.write_text(yaml_without_allowlist, encoding="utf-8")

    config = load_agents_config(config_file)

    assert config.agents[0].tool_allowlist is None
