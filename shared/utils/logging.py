import time
from contextvars import ContextVar
from functools import wraps
from uuid import uuid4

from loguru import logger

# Context variables for request-scoped logging
_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)
_account_id: ContextVar[int | None] = ContextVar("account_id", default=None)


def get_request_id() -> str | None:
    return _request_id.get()


def get_account_id() -> int | None:
    return _account_id.get()


def set_request_context(request_id: str | None = None, account_id: int | None = None):
    """Set request context for logging."""
    if request_id:
        _request_id.set(request_id)
    if account_id:
        _account_id.set(account_id)


def clear_request_context():
    """Clear request context."""
    _request_id.set(None)
    _account_id.set(None)


def generate_request_id() -> str:
    """Generate a short request ID."""
    return uuid4().hex[:12]


def _get_logger(module: str | None = None):
    """Get a logger with current request context bound."""
    ctx = {}

    if req_id := get_request_id():
        ctx["request_id"] = req_id
    if acc_id := get_account_id():
        ctx["account_id"] = acc_id
    if module:
        ctx["module"] = module

    return logger.bind(**ctx) if ctx else logger


def log_info(message: str, module: str | None = None, **kwargs):
    """Log INFO - use sparingly for key business events."""
    _get_logger(module).info(message, **kwargs)


def log_debug(message: str, module: str | None = None, **kwargs):
    """Log DEBUG - technical details for troubleshooting."""
    _get_logger(module).debug(message, **kwargs)


def log_warning(message: str, module: str | None = None, **kwargs):
    """Log WARNING - degraded but still working."""
    _get_logger(module).warning(message, **kwargs)


def log_error(message: str, module: str | None = None, **kwargs):
    """Log ERROR - something failed."""
    _get_logger(module).error(message, **kwargs)


class Timer:
    """Context manager for timing operations. Returns elapsed time."""

    def __init__(self):
        self.start_time = 0
        self.elapsed_ms = 0

    def __enter__(self):
        self.start_time = time.perf_counter_ns()
        return self

    def __exit__(self, *args):
        self.elapsed_ms = (time.perf_counter_ns() - self.start_time) / 1_000_000


def timed(module: str | None = None, operation: str | None = None):
    """Decorator that logs execution time at DEBUG level."""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            op_name = operation or func.__name__
            with Timer() as t:
                result = await func(*args, **kwargs)
            log_debug(f"{op_name} completed", module=module, duration_ms=round(t.elapsed_ms, 2))
            return result

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            op_name = operation or func.__name__
            with Timer() as t:
                result = func(*args, **kwargs)
            log_debug(f"{op_name} completed", module=module, duration_ms=round(t.elapsed_ms, 2))
            return result

        if asyncio_iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    return decorator


def asyncio_iscoroutinefunction(func) -> bool:
    """Check if function is async."""
    import asyncio
    return asyncio.iscoroutinefunction(func)
