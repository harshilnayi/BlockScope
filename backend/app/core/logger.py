import logging
from logging.handlers import RotatingFileHandler
import os
import contextvars
from pythonjsonlogger import jsonlogger

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

# Context var for request ID tracking
request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")

class RequestIdFilter(logging.Filter):
    """Filter to inject request ID into log records."""
    def filter(self, record: logging.LogRecord) -> bool:
        """Add request_id to log record."""
        record.request_id = request_id_var.get()
        return True

def setup_logger() -> logging.Logger:
    """Setup structured JSON logger with request ID tracking."""
    logger = logging.getLogger("blockscope")
    logger.setLevel(logging.INFO)

    # Avoid duplicate handlers if setup_logger is called multiple times
    if logger.handlers:
        return logger

    # JSON Formatter
    formatter = jsonlogger.JsonFormatter(
        "%(asctime)s %(levelname)s %(name)s %(request_id)s %(message)s",
        rename_fields={"levelname": "level", "asctime": "timestamp"}
    )

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.addFilter(RequestIdFilter())

    file_handler = RotatingFileHandler(
        f"{LOG_DIR}/app.log",
        maxBytes=5_000_000,
        backupCount=3
    )
    file_handler.setFormatter(formatter)
    file_handler.addFilter(RequestIdFilter())

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger

logger = setup_logger()
