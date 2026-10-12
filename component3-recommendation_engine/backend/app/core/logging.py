"""Structured logging helpers. Facial profiles are not logged by default."""

from __future__ import annotations

import logging
import sys
from typing import Any


def setup_logging(level: str = "INFO") -> None:
    root = logging.getLogger()
    if root.handlers:
        root.setLevel(level.upper())
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s %(levelname)s [%(name)s] request_id=%(request_id)s %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
    )
    root.addHandler(handler)
    root.setLevel(level.upper())


class RequestIdFilter(logging.Filter):
    def __init__(self, request_id: str = "-") -> None:
        super().__init__()
        self.request_id = request_id

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "request_id"):
            record.request_id = self.request_id
        return True


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    # Ensure request_id attribute exists for formatters when no middleware set it.
    logger.addFilter(RequestIdFilter("-"))
    return logger


def log_event(logger: logging.Logger, message: str, **fields: Any) -> None:
    """Log an operational event without including facial profile payloads."""
    extras = " ".join(f"{key}={value}" for key, value in fields.items())
    logger.info("%s %s", message, extras)
