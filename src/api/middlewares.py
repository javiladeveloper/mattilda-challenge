"""API Middlewares."""

import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from src.infrastructure.logging import get_logger

logger = get_logger("api.middleware")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging all requests and responses."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Start timer
        start_time = time.time()

        # Get request info
        method = request.method
        path = request.url.path
        client_ip = request.client.host if request.client else "unknown"

        # Log request
        logger.info(
            "request_started",
            method=method,
            path=path,
            client_ip=client_ip,
            query_params=str(request.query_params),
        )

        try:
            # Process request
            response = await call_next(request)

            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000

            # Log response
            log_method = logger.info if response.status_code < 400 else logger.warning
            log_method(
                "request_completed",
                method=method,
                path=path,
                status_code=response.status_code,
                duration_ms=round(duration_ms, 2),
            )

            # Add timing header
            response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"

            return response

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                "request_failed",
                method=method,
                path=path,
                error=str(e),
                duration_ms=round(duration_ms, 2),
            )
            raise


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware for collecting basic metrics."""

    def __init__(self, app):
        super().__init__(app)
        self.request_count = 0
        self.error_count = 0
        self.total_duration_ms = 0.0

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()

        try:
            response = await call_next(request)
            self.request_count += 1

            if response.status_code >= 400:
                self.error_count += 1

            duration_ms = (time.time() - start_time) * 1000
            self.total_duration_ms += duration_ms

            return response

        except Exception:
            self.request_count += 1
            self.error_count += 1
            raise

    def get_metrics(self) -> dict:
        """Get current metrics."""
        avg_duration = (
            self.total_duration_ms / self.request_count
            if self.request_count > 0
            else 0
        )
        return {
            "total_requests": self.request_count,
            "total_errors": self.error_count,
            "error_rate": (
                self.error_count / self.request_count
                if self.request_count > 0
                else 0
            ),
            "avg_duration_ms": round(avg_duration, 2),
        }
