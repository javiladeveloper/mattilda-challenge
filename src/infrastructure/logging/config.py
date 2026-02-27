"""Structured logging configuration using structlog."""

import logging
import sys
from typing import Any

import structlog
from structlog.types import Processor

from src.config import settings


def setup_logging() -> None:
    """Configure structured logging for the application."""

    # Determine if we're in debug mode
    if settings.debug:
        log_level = logging.DEBUG
        renderer: Processor = structlog.dev.ConsoleRenderer(colors=True)
    else:
        log_level = logging.INFO
        renderer = structlog.processors.JSONRenderer()

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.format_exc_info,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard logging to work with structlog
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )


def get_logger(name: str = None) -> structlog.BoundLogger:
    """Get a structured logger instance."""
    return structlog.get_logger(name)


class LoggerMiddleware:
    """Middleware for request/response logging."""

    def __init__(self, logger: structlog.BoundLogger = None):
        self.logger = logger or get_logger("api")

    async def log_request(
        self,
        method: str,
        path: str,
        client_ip: str = None,
        user_id: str = None,
    ) -> None:
        """Log incoming request."""
        self.logger.info(
            "request_received",
            method=method,
            path=path,
            client_ip=client_ip,
            user_id=user_id,
        )

    async def log_response(
        self,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
    ) -> None:
        """Log outgoing response."""
        log_method = self.logger.info if status_code < 400 else self.logger.warning
        log_method(
            "request_completed",
            method=method,
            path=path,
            status_code=status_code,
            duration_ms=round(duration_ms, 2),
        )

    async def log_error(
        self,
        method: str,
        path: str,
        error: str,
        exc_info: Any = None,
    ) -> None:
        """Log error."""
        self.logger.error(
            "request_error",
            method=method,
            path=path,
            error=error,
            exc_info=exc_info,
        )
