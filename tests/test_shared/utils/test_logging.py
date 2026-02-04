import asyncio
import time
from unittest.mock import patch


def test_timer_measures_elapsed_time():
    from shared.utils.logging import Timer

    with Timer() as t:
        time.sleep(0.01)

    assert t.elapsed_ms >= 10
    assert t.elapsed_ms < 100


def test_timer_elapsed_is_zero_before_exit():
    from shared.utils.logging import Timer

    t = Timer()
    assert t.elapsed_ms == 0


def test_timer_can_be_used_multiple_times():
    from shared.utils.logging import Timer

    t = Timer()

    with t:
        time.sleep(0.01)
    first_elapsed = t.elapsed_ms

    with t:
        time.sleep(0.02)
    second_elapsed = t.elapsed_ms

    assert second_elapsed > first_elapsed


def test_set_and_get_request_id():
    from shared.utils.logging import (
        clear_request_context,
        get_request_id,
        set_request_context,
    )

    set_request_context(request_id="test-123")
    assert get_request_id() == "test-123"
    clear_request_context()


def test_set_and_get_account_id():
    from shared.utils.logging import (
        clear_request_context,
        get_account_id,
        set_request_context,
    )

    set_request_context(account_id=42)
    assert get_account_id() == 42
    clear_request_context()


def test_clear_resets_context():
    from shared.utils.logging import (
        clear_request_context,
        get_account_id,
        get_request_id,
        set_request_context,
    )

    set_request_context(request_id="test", account_id=123)
    clear_request_context()

    assert get_request_id() is None
    assert get_account_id() is None


def test_generate_request_id_is_12_chars():
    from shared.utils.logging import generate_request_id

    req_id = generate_request_id()
    assert len(req_id) == 12
    assert all(c in "0123456789abcdef" for c in req_id)


def test_generate_request_id_is_unique():
    from shared.utils.logging import generate_request_id

    ids = [generate_request_id() for _ in range(100)]
    assert len(set(ids)) == 100


@patch("shared.utils.logging.logger")
def test_log_info_calls_logger(mock_logger):
    from shared.utils.logging import clear_request_context, log_info

    clear_request_context()
    log_info("test message", module="test", key="value")

    mock_logger.bind.assert_called()
    mock_logger.bind.return_value.info.assert_called_with("test message", key="value")


@patch("shared.utils.logging.logger")
def test_log_debug_calls_logger(mock_logger):
    from shared.utils.logging import clear_request_context, log_debug

    clear_request_context()
    log_debug("debug message", module="test")

    mock_logger.bind.assert_called()
    mock_logger.bind.return_value.debug.assert_called_with("debug message")


@patch("shared.utils.logging.logger")
def test_log_warning_calls_logger(mock_logger):
    from shared.utils.logging import clear_request_context, log_warning

    clear_request_context()
    log_warning("warning message", module="test")

    mock_logger.bind.assert_called()
    mock_logger.bind.return_value.warning.assert_called_with("warning message")


@patch("shared.utils.logging.logger")
def test_log_error_calls_logger(mock_logger):
    from shared.utils.logging import clear_request_context, log_error

    clear_request_context()
    log_error("error message", module="test")

    mock_logger.bind.assert_called()
    mock_logger.bind.return_value.error.assert_called_with("error message")


@patch("shared.utils.logging.logger")
def test_log_includes_request_context(mock_logger):
    from shared.utils.logging import (
        clear_request_context,
        log_info,
        set_request_context,
    )

    set_request_context(request_id="req-123", account_id=456)
    log_info("test", module="api")

    mock_logger.bind.assert_called_with(
        request_id="req-123", account_id=456, module="api"
    )
    clear_request_context()


@patch("shared.utils.logging.logger")
def test_log_without_module(mock_logger):
    from shared.utils.logging import clear_request_context, log_info

    clear_request_context()
    log_info("test")

    mock_logger.info.assert_called_with("test")


@patch("shared.utils.logging.logger")
def test_timed_sync_function(mock_logger):
    from shared.utils.logging import clear_request_context, timed

    clear_request_context()

    @timed(module="test")
    def my_func():
        return 42

    result = my_func()

    assert result == 42
    mock_logger.bind.return_value.debug.assert_called()


@patch("shared.utils.logging.logger")
def test_timed_async_function(mock_logger):
    from shared.utils.logging import clear_request_context, timed

    clear_request_context()

    @timed(module="test")
    async def my_async_func():
        return 42

    result = asyncio.run(my_async_func())

    assert result == 42
    mock_logger.bind.return_value.debug.assert_called()


@patch("shared.utils.logging.logger")
def test_timed_uses_function_name(mock_logger):
    from shared.utils.logging import clear_request_context, timed

    clear_request_context()

    @timed(module="test")
    def my_specific_func():
        pass

    my_specific_func()

    call_args = mock_logger.bind.return_value.debug.call_args
    assert "my_specific_func completed" in str(call_args)


@patch("shared.utils.logging.logger")
def test_timed_custom_operation_name(mock_logger):
    from shared.utils.logging import clear_request_context, timed

    clear_request_context()

    @timed(module="test", operation="custom_op")
    def my_func():
        pass

    my_func()

    call_args = mock_logger.bind.return_value.debug.call_args
    assert "custom_op completed" in str(call_args)


def test_timed_preserves_function_metadata():
    from shared.utils.logging import timed

    @timed(module="test")
    def my_func_with_doc():
        """My docstring."""
        pass

    assert my_func_with_doc.__name__ == "my_func_with_doc"
    assert my_func_with_doc.__doc__ == "My docstring."
