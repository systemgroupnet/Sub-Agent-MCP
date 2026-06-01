"""Configuration-related exceptions."""

from __future__ import annotations


class ConfigError(Exception):
    """Base exception for configuration errors."""


class ConfigFileNotFoundError(ConfigError):
    """Raised when the agents config file does not exist."""


class ConfigValidationError(ConfigError):
    """Raised when the agents config fails validation."""


class EnvVarNotFoundError(ConfigError):
    """Raised when a required environment variable is missing."""
