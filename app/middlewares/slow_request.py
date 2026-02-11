# The `SlowRequestMiddleware` class measures the duration of incoming HTTP requests and logs warnings
# or errors based on predefined thresholds for slow and very slow requests.
import time
import structlog
from starlette.middleware.base import BaseHTTPMiddleware

logger = structlog.get_logger("request")

SLOW_REQUEST_MS = 800        # warn
VERY_SLOW_REQUEST_MS = 2000 # error

class SlowRequestMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start = time.perf_counter()

        response = await call_next(request)

        duration_ms = round((time.perf_counter() - start) * 1000, 2)

        structlog.contextvars.bind_contextvars(
            duration_ms=duration_ms,
            path=request.url.path,
            method=request.method,
            status_code=response.status_code,
        )

        if duration_ms >= VERY_SLOW_REQUEST_MS:
            logger.warning("very_slow_request")
        elif duration_ms >= SLOW_REQUEST_MS:
            logger.warning("slow_request")

        return response
