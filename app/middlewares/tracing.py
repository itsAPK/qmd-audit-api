import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.config import settings
from app.core.logging import trace_id_ctx, span_id_ctx


request_logger = structlog.get_logger("request")

# Thresholds (configurable via settings)
SLOW_REQUEST_MS = getattr(settings, "SLOW_REQUEST_MS", 800)
VERY_SLOW_REQUEST_MS = getattr(settings, "VERY_SLOW_REQUEST_MS", 2000)


class TraceAndTimingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that adds:
    - trace_id / span_id
    - request duration (ms)
    - slow request warnings
    - client context (ip, user-agent)
    """

    async def dispatch(self, request: Request, call_next):
        # ---- Trace context ----
        trace_id = uuid.uuid4().hex
        span_id = uuid.uuid4().hex[:16]

        trace_id_ctx.set(trace_id)
        span_id_ctx.set(span_id)

        # ---- Request start ----
        start = time.perf_counter()

        client_ip = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")

        structlog.contextvars.bind_contextvars(
            path=request.url.path,
            method=request.method,
            client_ip=client_ip,
            user_agent=user_agent,
        )

        # ---- Execute request ----
        response = await call_next(request)

        # ---- Timing & response ----
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        response_size = int(response.headers.get("content-length", 0))

        structlog.contextvars.bind_contextvars(
            duration_ms=duration_ms,
            status_code=response.status_code,
            response_size=response_size,
        )

        # ---- Slow request alerts ----
        if duration_ms >= VERY_SLOW_REQUEST_MS:
            request_logger.error("very_slow_request")
        elif duration_ms >= SLOW_REQUEST_MS:
            request_logger.warning("slow_request")

        # ---- Response headers ----
        response.headers["X-Trace-Id"] = trace_id

        return response
