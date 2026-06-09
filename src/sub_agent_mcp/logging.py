"""Structured logging setup."""

from __future__ import annotations

import logging
import sys
from collections.abc import Iterator
from contextlib import contextmanager

import structlog


def setup_logging(level: str = "INFO") -> None:
    """Configure structlog and stdlib logging."""
    log_level = getattr(logging, level.upper(), logging.INFO)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )

    logging.basicConfig(level=log_level, format="%(message)s", stream=sys.stdout)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)


@contextmanager
def agent_log_context(*, trace_id: str, model_id: str, agent_id: str) -> Iterator[None]:
    """Bind per-agent execution fields to structlog contextvars."""
    structlog.contextvars.bind_contextvars(
        trace_id=trace_id,
        model_id=model_id,
        agent_id=agent_id,
    )
    try:
        yield
    finally:
        structlog.contextvars.clear_contextvars()
