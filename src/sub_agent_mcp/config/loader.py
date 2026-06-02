"""YAML configuration loader with environment variable substitution."""

from __future__ import annotations

import os
import re
from pathlib import Path

import yaml
from pydantic import ValidationError

from sub_agent_mcp.config.errors import (
    ConfigFileNotFoundError,
    ConfigValidationError,
    EnvVarNotFoundError,
)
from sub_agent_mcp.config.schema import AgentConfig, AgentsFile

ENV_VAR_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?::-([^}]*))?\}")

DEFAULT_CONFIG_PATH = Path("config/agents.yaml")


def substitute_env_vars(text: str) -> str:
    """Replace ${VAR} and ${VAR:-default} placeholders with environment values."""

    def replacer(match: re.Match[str]) -> str:
        var_name = match.group(1)
        default = match.group(2)
        value = os.environ.get(var_name)
        if value is not None:
            return value
        if default is not None:
            return default
        raise EnvVarNotFoundError(
            f"Environment variable '{var_name}' is not set and has no default"
        )

    return ENV_VAR_PATTERN.sub(replacer, text)


def load_agents_config(path: Path | str | None = None) -> AgentsFile:
    """Load and validate agents configuration from a YAML file."""
    config_path = Path(path or os.getenv("AGENTS_CONFIG_PATH", DEFAULT_CONFIG_PATH))

    if not config_path.exists():
        raise ConfigFileNotFoundError(f"Agents config file not found: {config_path}")

    raw_text = config_path.read_text(encoding="utf-8")
    substituted = substitute_env_vars(raw_text)

    try:
        data = yaml.safe_load(substituted)
    except yaml.YAMLError as exc:
        raise ConfigValidationError(f"Invalid YAML in {config_path}: {exc}") from exc

    if not isinstance(data, dict):
        raise ConfigValidationError(f"Config root must be a mapping, got {type(data).__name__}")

    try:
        return AgentsFile.model_validate(data)
    except ValidationError as exc:
        raise ConfigValidationError(f"Config validation failed for {config_path}: {exc}") from exc


def get_agent_by_id(config: AgentsFile, agent_id: str) -> AgentConfig:
    """Return an agent by id or raise ConfigValidationError."""
    agent = config.get_agent(agent_id)
    if agent is None:
        raise ConfigValidationError(f"Agent not found: {agent_id}")
    return agent
