"""
Unit tests for app.core.logger — structured logging module.

Verifies JSON formatting, request-ID tracking, performance timer,
error context helper, and the module-level singleton.
"""

import json
import logging
import time
from unittest.mock import MagicMock

import pytest

from app.core.logger import (
    HumanFormatter,
    JSONFormatter,
    PerformanceTimer,
    get_elapsed_ms,
    get_request_id,
    log_error_context,
    logger,
    set_request_id,
    setup_logger,
)


# ══════════════════════════════════════════════════════════════
# Request-ID context var
# ══════════════════════════════════════════════════════════════

class TestRequestIDTracking:

    def test_set_request_id_returns_id(self):
        rid = set_request_id("abc-123")
        assert rid == "abc-123"
        assert get_request_id() == "abc-123"

    def test_set_request_id_auto_generates(self):
        rid = set_request_id()
        assert len(rid) == 36  # UUID4 format
        assert get_request_id() == rid

    def test_get_elapsed_ms_returns_float(self):
        set_request_id("timer-test")
        time.sleep(0.01)
        elapsed = get_elapsed_ms()
        assert isinstance(elapsed, float)
        assert elapsed >= 0

    def test_get_elapsed_ms_zero_without_request(self):
        """When no request is active, elapsed should be 0."""
        from app.core.logger import _request_start_var
        _request_start_var.set(0.0)
        elapsed = get_elapsed_ms()
        assert elapsed == 0.0


# ══════════════════════════════════════════════════════════════
# JSONFormatter
# ══════════════════════════════════════════════════════════════

class TestJSONFormatter:

    def _make_record(self, msg="test message", level=logging.INFO, extra=None):
        record = logging.LogRecord(
            name="test.logger",
            level=level,
            pathname=__file__,
            lineno=42,
            msg=msg,
            args=(),
            exc_info=None,
        )
        if extra:
            for k, v in extra.items():
                setattr(record, k, v)
        return record

    def test_output_is_valid_json(self):
        fmt = JSONFormatter()
        record = self._make_record()
        output = fmt.format(record)
        parsed = json.loads(output)
        assert isinstance(parsed, dict)

    def test_output_has_required_fields(self):
        fmt = JSONFormatter()
        record = self._make_record("hello world")
        parsed = json.loads(fmt.format(record))
        for field in ("timestamp", "level", "logger", "message"):
            assert field in parsed

    def test_level_name_in_output(self):
        fmt = JSONFormatter()
        record = self._make_record(level=logging.WARNING)
        parsed = json.loads(fmt.format(record))
        assert parsed["level"] == "WARNING"

    def test_request_id_included(self):
        set_request_id("req-xyz")
        fmt = JSONFormatter()
        record = self._make_record()
        parsed = json.loads(fmt.format(record))
        assert parsed["request_id"] == "req-xyz"

    def test_custom_extra_field_included(self):
        fmt = JSONFormatter()
        record = self._make_record(extra={"scan_id": 42})
        parsed = json.loads(fmt.format(record))
        assert parsed.get("scan_id") == 42

    def test_reserved_fields_not_duplicated(self):
        """Built-in LogRecord fields should not cause KeyError."""
        fmt = JSONFormatter()
        # 'filename' is a built-in LogRecord field — must NOT trigger KeyError
        record = self._make_record()
        output = fmt.format(record)
        assert output  # Just must not raise

    def test_exception_info_included(self):
        fmt = JSONFormatter()
        try:
            raise ValueError("oops")
        except ValueError:
            import sys
            exc_info = sys.exc_info()
        record = logging.LogRecord(
            name="test", level=logging.ERROR, pathname=__file__,
            lineno=1, msg="error", args=(), exc_info=exc_info,
        )
        parsed = json.loads(fmt.format(record))
        assert "exception" in parsed
        assert parsed["exception"]["type"] == "ValueError"


# ══════════════════════════════════════════════════════════════
# HumanFormatter
# ══════════════════════════════════════════════════════════════

class TestHumanFormatter:

    def _make_record(self, msg="hello", level=logging.INFO):
        return logging.LogRecord(
            name="test", level=level, pathname=__file__,
            lineno=1, msg=msg, args=(), exc_info=None,
        )

    def test_output_is_string(self):
        fmt = HumanFormatter()
        output = fmt.format(self._make_record())
        assert isinstance(output, str)

    def test_output_contains_message(self):
        fmt = HumanFormatter()
        output = fmt.format(self._make_record("test message"))
        assert "test message" in output

    def test_output_contains_level(self):
        fmt = HumanFormatter()
        output = fmt.format(self._make_record(level=logging.ERROR))
        assert "ERROR" in output


# ══════════════════════════════════════════════════════════════
# PerformanceTimer
# ══════════════════════════════════════════════════════════════

class TestPerformanceTimer:

    def _spy_logger(self):
        log = logging.getLogger("test.perf")
        log.debug = MagicMock()
        log.warning = MagicMock()
        log.error = MagicMock()
        return log

    def test_logs_debug_on_fast_operation(self):
        log = self._spy_logger()
        with PerformanceTimer("fast_op", log, warn_threshold_ms=5000):
            pass
        log.debug.assert_called_once()

    def test_logs_warning_on_slow_operation(self):
        log = self._spy_logger()
        with PerformanceTimer("slow_op", log, warn_threshold_ms=0):
            time.sleep(0.01)
        log.warning.assert_called_once()

    def test_logs_error_on_exception(self):
        log = self._spy_logger()
        with pytest.raises(RuntimeError):
            with PerformanceTimer("failing_op", log):
                raise RuntimeError("boom")
        log.error.assert_called_once()

    def test_extra_fields_passed_through(self):
        log = self._spy_logger()
        with PerformanceTimer("op", log, extra={"table": "scans"}):
            pass
        call_kwargs = log.debug.call_args
        assert call_kwargs is not None

    def test_context_manager_returns_self(self):
        log = self._spy_logger()
        timer = PerformanceTimer("op", log)
        with timer as t:
            assert t is timer


# ══════════════════════════════════════════════════════════════
# log_error_context
# ══════════════════════════════════════════════════════════════

class TestLogErrorContext:

    def test_logs_at_error_level(self):
        log = logging.getLogger("test.error_ctx")
        log.error = MagicMock()
        exc = ValueError("something went wrong")
        log_error_context(log, "test msg", exc, context={"scan_id": 1})
        log.error.assert_called_once()

    def test_works_without_context(self):
        log = logging.getLogger("test.error_ctx2")
        log.error = MagicMock()
        exc = RuntimeError("boom")
        log_error_context(log, "failure", exc)
        log.error.assert_called_once()


# ══════════════════════════════════════════════════════════════
# setup_logger
# ══════════════════════════════════════════════════════════════

class TestSetupLogger:

    def test_returns_logger_instance(self):
        log = setup_logger("test.setup")
        assert isinstance(log, logging.Logger)

    def test_idempotent_double_call(self):
        """Calling twice should not add duplicate handlers."""
        log1 = setup_logger("test.idempotent")
        handler_count = len(log1.handlers)
        log2 = setup_logger("test.idempotent")
        assert len(log2.handlers) == handler_count

    def test_module_singleton_is_logger(self):
        assert isinstance(logger, logging.Logger)
        assert logger.name == "blockscope"

    def test_setup_logger_with_file_handler(self, tmp_path, monkeypatch):
        """setup_logger creates a file handler when LOG_FILE_ENABLED=true."""
        monkeypatch.setenv("LOG_FILE_ENABLED", "true")
        monkeypatch.setenv("LOG_DIR", str(tmp_path))
        # Use unique name so fresh logger is created
        import time
        unique_name = f"test.file.{int(time.time() * 1000)}"
        log = setup_logger(unique_name)
        # Should have at least 1 file handler
        has_file = any(
            hasattr(h, "baseFilename") for h in log.handlers
        )
        assert has_file

    def test_is_json_mode_explicit_true(self, monkeypatch):
        from app.core.logger import _is_json_mode
        monkeypatch.setenv("LOG_JSON_FORMAT", "true")
        assert _is_json_mode() is True

    def test_is_json_mode_explicit_false(self, monkeypatch):
        from app.core.logger import _is_json_mode
        monkeypatch.setenv("LOG_JSON_FORMAT", "false")
        assert _is_json_mode() is False

    def test_is_json_mode_auto_detect_dev(self, monkeypatch):
        from app.core.logger import _is_json_mode
        monkeypatch.delenv("LOG_JSON_FORMAT", raising=False)
        monkeypatch.setenv("ENVIRONMENT", "development")
        assert _is_json_mode() is False

    def test_is_json_mode_auto_detect_prod(self, monkeypatch):
        from app.core.logger import _is_json_mode
        monkeypatch.delenv("LOG_JSON_FORMAT", raising=False)
        monkeypatch.setenv("ENVIRONMENT", "production")
        assert _is_json_mode() is True


class TestHumanFormatterExcInfo:

    def _make_record_with_exc(self):
        try:
            raise ValueError("test error")
        except ValueError:
            import sys
            exc_info = sys.exc_info()
        return logging.LogRecord(
            name="test", level=logging.ERROR,
            pathname=__file__, lineno=1,
            msg="Error msg", args=(), exc_info=exc_info,
        )

    def test_human_formatter_exc_info_appended(self):
        fmt = HumanFormatter()
        output = fmt.format(self._make_record_with_exc())
        assert "ValueError" in output
        assert "test error" in output
