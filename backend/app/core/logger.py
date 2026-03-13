"""
BlockScope Logging Module.

Provides structured JSON logging with:
- Request ID tracking (per-request correlation)
- Performance timing helpers
- Error context capture
- Rotating file handler
- Environment-aware formatting (JSON in prod, human-readable in dev)
"""

import json
import logging
import os
import time
import traceback
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from typing import Any, Dict, Optional

# ──────────────────────────────────────────────
# Context variable for per-request tracking
# ──────────────────────────────────────────────
_request_id_var: ContextVar[str] = ContextVar("request_id", default="")
_request_start_var: ContextVar[float] = ContextVar("request_start", default=0.0)


def get_request_id() -> str:
    """Return the current request's ID, or generate a fallback."""
    return _request_id_var.get() or "no-request"


def set_request_id(request_id: Optional[str] = None) -> str:
    """
    Set the request ID for the current async context.

    Args:
        request_id: Explicit ID to use; auto-generates a UUID4 if omitted.

    Returns:
        The request ID that was set.
    """
    rid = request_id or str(uuid.uuid4())
    _request_id_var.set(rid)
    _request_start_var.set(time.perf_counter())
    return rid


def get_elapsed_ms() -> float:
    """
    Return elapsed milliseconds since the request started.

    Returns:
        Elapsed time in milliseconds, or 0.0 if no request is active.
    """
    start = _request_start_var.get()
    if start == 0.0:
        return 0.0
    return round((time.perf_counter() - start) * 1000, 2)


# ──────────────────────────────────────────────
# JSON log formatter
# ──────────────────────────────────────────────

class JSONFormatter(logging.Formatter):
    """
    Formats log records as single-line JSON objects.

    Each record includes timestamp, level, logger name, message,
    request ID, elapsed time, and any extra context fields.
    """

    def format(self, record: logging.LogRecord) -> str:
        """
        Serialize a LogRecord to a JSON string.

        Args:
            record: The log record to format.

        Returns:
            JSON-encoded log line.
        """
        payload: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": get_request_id(),
            "elapsed_ms": get_elapsed_ms(),
        }

        # Include module / function context
        payload["module"] = record.module
        payload["func"] = record.funcName
        payload["line"] = record.lineno

        # Attach exception info when present
        if record.exc_info:
            payload["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info),
            }

        # Attach any extra fields passed via `extra={\"key\": value}`
        # IMPORTANT: exclude ALL built-in LogRecord attributes to prevent
        # KeyError: \"Attempt to overwrite '<attr>' in LogRecord\"
        _RESERVED = frozenset({
            "args", "asctime", "created", "exc_info", "exc_text",
            "filename", "funcName", "id", "levelname", "levelno",
            "lineno", "message", "module", "msecs", "msg", "name",
            "pathname", "process", "processName", "relativeCreated",
            "stack_info", "thread", "threadName", "taskName",
        })
        for key, value in record.__dict__.items():
            if key not in _RESERVED and not key.startswith("_"):
                payload[key] = value

        return json.dumps(payload, default=str)


class HumanFormatter(logging.Formatter):
    """
    Human-readable formatter for development environments.

    Format: TIMESTAMP | LEVEL     | REQUEST_ID | ELAPSED | logger: message
    """

    LEVEL_COLORS = {
        "DEBUG":    "\033[36m",   # Cyan
        "INFO":     "\033[32m",   # Green
        "WARNING":  "\033[33m",   # Yellow
        "ERROR":    "\033[31m",   # Red
        "CRITICAL": "\033[35m",   # Magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        """
        Format the log record for human readability.

        Args:
            record: The log record to format.

        Returns:
            Formatted log line string.
        """
        color = self.LEVEL_COLORS.get(record.levelname, "")
        reset = self.RESET
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        rid = get_request_id()
        elapsed = get_elapsed_ms()
        elapsed_str = f"{elapsed:>8.1f}ms" if elapsed else "        -  "

        base = (
            f"{ts} | {color}{record.levelname:<8}{reset} | "
            f"{rid[:8]:<8} | {elapsed_str} | {record.name}: {record.getMessage()}"
        )

        if record.exc_info:
            base += "\n" + self.formatException(record.exc_info)

        return base


# ──────────────────────────────────────────────
# Logger factory
# ──────────────────────────────────────────────

def _get_log_level() -> int:
    """Resolve log level from LOG_LEVEL env var (default INFO)."""
    level_str = os.getenv("LOG_LEVEL", "INFO").upper()
    return getattr(logging, level_str, logging.INFO)


def _is_json_mode() -> bool:
    """Use JSON format unless explicitly disabled (development mode)."""
    env = os.getenv("ENVIRONMENT", "development").lower()
    json_env = os.getenv("LOG_JSON_FORMAT", "").lower()
    if json_env in ("true", "1", "yes"):
        return True
    if json_env in ("false", "0", "no"):
        return False
    # Auto-detect: JSON for non-dev environments
    return env not in ("development", "dev", "local")


def setup_logger(name: str = "blockscope") -> logging.Logger:
    """
    Build and configure the BlockScope application logger.

    Features:
    - Structured JSON output (production) or human-readable (development)
    - Console handler always active
    - Rotating file handler (configurable via env vars)
    - Request ID injected automatically via context var

    Args:
        name: Logger name (default: "blockscope").

    Returns:
        Configured Logger instance.
    """
    logger = logging.getLogger(name)

    # Avoid double-adding handlers if already configured
    if logger.handlers:
        return logger

    level = _get_log_level()
    logger.setLevel(level)
    logger.propagate = False

    # Choose formatter based on environment
    formatter: logging.Formatter = (
        JSONFormatter() if _is_json_mode() else HumanFormatter()
    )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Rotating file handler
    log_file_enabled = os.getenv("LOG_FILE_ENABLED", "true").lower() in ("true", "1", "yes")
    if log_file_enabled:
        log_dir = os.getenv("LOG_DIR", "logs")
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, "app.log")
        max_bytes = int(os.getenv("LOG_FILE_MAX_BYTES", str(10 * 1024 * 1024)))  # 10 MB
        backup_count = int(os.getenv("LOG_FILE_BACKUP_COUNT", "5"))

        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        file_handler.setLevel(level)
        # File handler always uses JSON for machine-parseable logs
        file_handler.setFormatter(JSONFormatter())
        logger.addHandler(file_handler)

    return logger


# ──────────────────────────────────────────────
# Performance logging helpers
# ──────────────────────────────────────────────

class PerformanceTimer:
    """
    Context manager for logging operation duration.

    Usage::

        with PerformanceTimer("database_query", logger, extra={"table": "scans"}):
            results = db.query(Scan).all()
    """

    def __init__(
        self,
        operation: str,
        log: logging.Logger,
        warn_threshold_ms: float = 500.0,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Initialise the timer.

        Args:
            operation: Human-readable name for the timed operation.
            log: Logger to emit timing records to.
            warn_threshold_ms: Log at WARNING if duration exceeds this (ms).
            extra: Optional extra fields to attach to the log record.
        """
        self.operation = operation
        self.log = log
        self.warn_threshold_ms = warn_threshold_ms
        self.extra: Dict[str, Any] = extra or {}
        self._start: float = 0.0

    def __enter__(self) -> "PerformanceTimer":
        self._start = time.perf_counter()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        elapsed_ms = round((time.perf_counter() - self._start) * 1000, 2)
        log_extra = {"operation": self.operation, "duration_ms": elapsed_ms, **self.extra}

        if exc_type is not None:
            self.log.error(
                "Operation '%s' failed after %.1f ms",
                self.operation,
                elapsed_ms,
                extra=log_extra,
                exc_info=True,
            )
        elif elapsed_ms > self.warn_threshold_ms:
            self.log.warning(
                "Slow operation '%s' completed in %.1f ms",
                self.operation,
                elapsed_ms,
                extra=log_extra,
            )
        else:
            self.log.debug(
                "Operation '%s' completed in %.1f ms",
                self.operation,
                elapsed_ms,
                extra=log_extra,
            )


def log_error_context(
    log: logging.Logger,
    message: str,
    error: Exception,
    context: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Log an exception with structured context fields.

    Args:
        log: Logger to use.
        message: Human-readable description of what failed.
        error: The exception that was raised.
        context: Additional context fields (e.g., contract_name, scan_id).
    """
    extra: Dict[str, Any] = {
        "error_type": type(error).__name__,
        "error_message": str(error),
        **(context or {}),
    }
    log.error(message, exc_info=error, extra=extra)


# ──────────────────────────────────────────────
# Module-level singleton logger
# ──────────────────────────────────────────────
logger = setup_logger("blockscope")
