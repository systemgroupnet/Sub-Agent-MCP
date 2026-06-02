"""Pydantic models for agent configuration."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    SecretStr,
    field_validator,
    model_validator,
)

AGENT_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_-]*$")


ReasoningEffort = Literal["none", "minimal", "low", "medium", "high", "xhigh"]
ReasoningSummary = Literal["auto", "concise", "detailed"]
Verbosity = Literal["low", "medium", "high"]


class LLMConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    base_uri: HttpUrl
    api_key: SecretStr
    model_id: str = Field(min_length=1)
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, ge=1)
    reasoning_effort: ReasoningEffort | None = None
    reasoning_summary: ReasoningSummary | None = None
    verbosity: Verbosity | None = None


class MCPServerConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    transport: Literal["streamable_http"]
    url: HttpUrl
    bearer_token: SecretStr | None = None
    headers: dict[str, str] = Field(default_factory=dict)


class AgentConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    llm: LLMConfig
    system_prompt: str = Field(min_length=1)
    mcp_servers: list[MCPServerConfig] = Field(default_factory=list)
    tool_allowlist: list[str] | None = None

    @field_validator("id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        if not AGENT_ID_PATTERN.match(value):
            msg = (
                f"Agent id '{value}' is invalid. "
                "Must start with a lowercase letter and contain only lowercase letters, "
                "digits, hyphens, or underscores."
            )
            raise ValueError(msg)
        return value


class AgentsFile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agents: list[AgentConfig] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_ids(self) -> AgentsFile:
        ids = [agent.id for agent in self.agents]
        duplicates = {agent_id for agent_id in ids if ids.count(agent_id) > 1}
        if duplicates:
            dup_list = ", ".join(sorted(duplicates))
            raise ValueError(f"Duplicate agent ids found: {dup_list}")
        return self

    def get_agent(self, agent_id: str) -> AgentConfig | None:
        for agent in self.agents:
            if agent.id == agent_id:
                return agent
        return None
