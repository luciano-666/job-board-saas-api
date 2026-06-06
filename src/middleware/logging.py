import time
import uuid
from collections.abc import Callable

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = structlog.get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Attach a unique request_id to every request and emit structured logs.

    Each request gets a UUID written into:
      - The structlog context (visible in all log calls during the request)
      - The response header ``X-Request-ID`` (useful for client-side tracing)

    Log format (JSON via structlog):
        {"event": "request_finished", "request_id": "...", "method": "GET",
         "path": "/api/v1/jobs", "status_code": 200, "duration_ms": 12.4, ...}
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = str(uuid.uuid4())

        # Bind request_id for all structlog calls in this request context.
        # structlog.contextvars is async-safe: uses contextvars under the hood.
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )

        start = time.perf_counter()

        try:
            response: Response = await call_next(request)
        except Exception:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            await logger.aerror(
                "request_failed",
                duration_ms=duration_ms,
                exc_info=True,
            )
            raise

        duration_ms = round((time.perf_counter() - start) * 1000, 2)

        await logger.ainfo(
            "request_finished",
            status_code=response.status_code,
            duration_ms=duration_ms,
        )

        response.headers["X-Request-ID"] = request_id
        return response
