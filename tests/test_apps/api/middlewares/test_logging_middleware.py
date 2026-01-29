import asyncio
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_request():
    request = MagicMock()
    request.method = "GET"
    request.url.path = "/api/v1/test"
    return request


@pytest.fixture
def mock_response():
    response = MagicMock()
    response.status_code = 200
    response.headers = {}
    return response


@patch("apps.api.middlewares.logging_middleware.log_info")
@patch("apps.api.middlewares.logging_middleware.clear_request_context")
@patch("apps.api.middlewares.logging_middleware.set_request_context")
@patch("apps.api.middlewares.logging_middleware.generate_request_id")
def test_sets_request_context(
    mock_gen_id,
    mock_set_ctx,
    mock_clear_ctx,
    mock_log_info,
    mock_request,
    mock_response,
):
    from apps.api.middlewares.logging_middleware import RequestLoggingMiddleware

    mock_gen_id.return_value = "abc123def456"

    middleware = RequestLoggingMiddleware(app=MagicMock())

    async def call_next(request):
        return mock_response

    asyncio.run(middleware.dispatch(mock_request, call_next))

    mock_set_ctx.assert_called_with(request_id="abc123def456")


@patch("apps.api.middlewares.logging_middleware.log_info")
@patch("apps.api.middlewares.logging_middleware.clear_request_context")
@patch("apps.api.middlewares.logging_middleware.set_request_context")
@patch("apps.api.middlewares.logging_middleware.generate_request_id")
def test_clears_context_after_request(
    mock_gen_id,
    mock_set_ctx,
    mock_clear_ctx,
    mock_log_info,
    mock_request,
    mock_response,
):
    from apps.api.middlewares.logging_middleware import RequestLoggingMiddleware

    mock_gen_id.return_value = "abc123"

    middleware = RequestLoggingMiddleware(app=MagicMock())

    async def call_next(request):
        return mock_response

    asyncio.run(middleware.dispatch(mock_request, call_next))

    mock_clear_ctx.assert_called_once()


@patch("apps.api.middlewares.logging_middleware.log_info")
@patch("apps.api.middlewares.logging_middleware.clear_request_context")
@patch("apps.api.middlewares.logging_middleware.set_request_context")
@patch("apps.api.middlewares.logging_middleware.generate_request_id")
def test_adds_request_id_to_response_headers(
    mock_gen_id,
    mock_set_ctx,
    mock_clear_ctx,
    mock_log_info,
    mock_request,
    mock_response,
):
    from apps.api.middlewares.logging_middleware import RequestLoggingMiddleware

    mock_gen_id.return_value = "req-id-123"

    middleware = RequestLoggingMiddleware(app=MagicMock())

    async def call_next(request):
        return mock_response

    result = asyncio.run(middleware.dispatch(mock_request, call_next))

    assert result.headers["X-Request-ID"] == "req-id-123"


@patch("apps.api.middlewares.logging_middleware.log_info")
@patch("apps.api.middlewares.logging_middleware.clear_request_context")
@patch("apps.api.middlewares.logging_middleware.set_request_context")
@patch("apps.api.middlewares.logging_middleware.generate_request_id")
def test_logs_request_info(
    mock_gen_id,
    mock_set_ctx,
    mock_clear_ctx,
    mock_log_info,
    mock_request,
    mock_response,
):
    from apps.api.middlewares.logging_middleware import RequestLoggingMiddleware

    mock_gen_id.return_value = "abc123"
    mock_request.method = "POST"
    mock_request.url.path = "/api/v1/statuses"
    mock_response.status_code = 201

    middleware = RequestLoggingMiddleware(app=MagicMock())

    async def call_next(request):
        return mock_response

    asyncio.run(middleware.dispatch(mock_request, call_next))

    mock_log_info.assert_called_once()
    call_kwargs = mock_log_info.call_args[1]

    assert call_kwargs["module"] == "api"
    assert call_kwargs["method"] == "POST"
    assert call_kwargs["path"] == "/api/v1/statuses"
    assert call_kwargs["status"] == 201
    assert "duration_ms" in call_kwargs


@patch("apps.api.middlewares.logging_middleware.log_info")
@patch("apps.api.middlewares.logging_middleware.clear_request_context")
@patch("apps.api.middlewares.logging_middleware.set_request_context")
@patch("apps.api.middlewares.logging_middleware.generate_request_id")
def test_returns_response(
    mock_gen_id,
    mock_set_ctx,
    mock_clear_ctx,
    mock_log_info,
    mock_request,
    mock_response,
):
    from apps.api.middlewares.logging_middleware import RequestLoggingMiddleware

    mock_gen_id.return_value = "abc123"

    middleware = RequestLoggingMiddleware(app=MagicMock())

    async def call_next(request):
        return mock_response

    result = asyncio.run(middleware.dispatch(mock_request, call_next))

    assert result is mock_response


@patch("apps.api.middlewares.logging_middleware.log_info")
@patch("apps.api.middlewares.logging_middleware.clear_request_context")
@patch("apps.api.middlewares.logging_middleware.set_request_context")
@patch("apps.api.middlewares.logging_middleware.generate_request_id")
def test_measures_request_duration(
    mock_gen_id,
    mock_set_ctx,
    mock_clear_ctx,
    mock_log_info,
    mock_request,
    mock_response,
):
    from apps.api.middlewares.logging_middleware import RequestLoggingMiddleware

    mock_gen_id.return_value = "abc123"

    middleware = RequestLoggingMiddleware(app=MagicMock())

    async def slow_call_next(request):
        await asyncio.sleep(0.01)
        return mock_response

    asyncio.run(middleware.dispatch(mock_request, slow_call_next))

    call_kwargs = mock_log_info.call_args[1]
    assert call_kwargs["duration_ms"] >= 10
