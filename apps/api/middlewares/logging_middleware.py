from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from shared.utils.logging import (
    Timer,
    clear_request_context,
    generate_request_id,
    log_info,
    set_request_context,
)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware that sets request context and logs request summary."""

    async def dispatch(self, request: Request, call_next):
        request_id = generate_request_id()
        set_request_context(request_id=request_id)

        # Add request_id to response headers for debugging
        with Timer() as t:
            response = await call_next(request)

        # Single INFO log per request
        log_info(
            "Request completed",
            module="api",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=round(t.elapsed_ms, 2),
        )

        response.headers["X-Request-ID"] = request_id
        clear_request_context()

        return response
