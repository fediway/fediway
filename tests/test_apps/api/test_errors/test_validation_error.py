from unittest.mock import MagicMock, patch

import pytest
from fastapi.exceptions import RequestValidationError

from apps.api.errors.validation_error import http422_error_handler


@pytest.fixture
def mock_request():
    return MagicMock()


@pytest.mark.asyncio
async def test_handler_removes_input_from_errors(mock_request):
    """Verify that 'input' field is removed from validation errors."""
    errors = [
        {
            "type": "missing",
            "loc": ("body", "name"),
            "msg": "Field required",
            "input": "sensitive_data",
        },
        {"type": "string_type", "loc": ("body", "email"), "msg": "Invalid email", "input": "bad@"},
    ]

    exc = MagicMock(spec=RequestValidationError)
    exc.errors.return_value = errors

    with patch("apps.api.errors.validation_error.log_error"):
        response = await http422_error_handler(mock_request, exc)

    assert response.status_code == 422
    # Verify input was removed from both errors
    assert "input" not in errors[0]
    assert "input" not in errors[1]


@pytest.mark.asyncio
async def test_handler_returns_422_status(mock_request):
    exc = MagicMock(spec=RequestValidationError)
    exc.errors.return_value = []

    response = await http422_error_handler(mock_request, exc)

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_handler_returns_generic_message(mock_request):
    exc = MagicMock(spec=RequestValidationError)
    exc.errors.return_value = []

    response = await http422_error_handler(mock_request, exc)

    import json

    body = json.loads(response.body)
    assert body == {"message": "invalid request"}


@pytest.mark.asyncio
async def test_handler_logs_each_error(mock_request):
    errors = [
        {"type": "missing", "loc": ("body", "name"), "msg": "Field required"},
        {"type": "string_type", "loc": ("body", "email"), "msg": "Invalid email"},
    ]

    exc = MagicMock(spec=RequestValidationError)
    exc.errors.return_value = errors

    with patch("apps.api.errors.validation_error.log_error") as mock_log:
        await http422_error_handler(mock_request, exc)

    assert mock_log.call_count == 2


@pytest.mark.asyncio
async def test_handler_handles_errors_without_input_field(mock_request):
    """Verify handler works when errors don't have 'input' field."""
    errors = [
        {"type": "missing", "loc": ("body", "name"), "msg": "Field required"},
    ]

    exc = MagicMock(spec=RequestValidationError)
    exc.errors.return_value = errors

    with patch("apps.api.errors.validation_error.log_error"):
        response = await http422_error_handler(mock_request, exc)

    assert response.status_code == 422
