import logging
import logging.handlers
from pathlib import Path

LOGS_DIR = Path("logs")


def setup_logging():
    LOGS_DIR.mkdir(exist_ok=True)
    LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))

    file_handler = logging.handlers.RotatingFileHandler(
        filename=LOGS_DIR / "blockscope.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))

    error_handler = logging.handlers.RotatingFileHandler(
        filename=LOGS_DIR / "errors.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    existing_files = [
        h.baseFilename
        for h in root_logger.handlers
        if isinstance(h, logging.handlers.RotatingFileHandler)
    ]

    if str(LOGS_DIR / "blockscope.log") not in existing_files:
        root_logger.addHandler(file_handler)

    if str(LOGS_DIR / "errors.log") not in existing_files:
        root_logger.addHandler(error_handler)

    if not any(
        isinstance(h, logging.StreamHandler)
        and not isinstance(h, logging.handlers.RotatingFileHandler)
        for h in root_logger.handlers
    ):
        root_logger.addHandler(console_handler)

    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    return root_logger
