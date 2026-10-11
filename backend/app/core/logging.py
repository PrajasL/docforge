import logging
import sys
from typing import Any, Dict


class StructuredFormatter(logging.Formatter):
    """Formats log messages into readable structured text or JSON-like log entries."""

    def format(self, record: logging.LogRecord) -> str:
        timestamp = self.formatTime(record, self.datefmt)
        level = record.levelname
        message = record.getMessage()
        name = record.name

        extra_info: Dict[str, Any] = {}
        if hasattr(record, "request_id"):
            extra_info["request_id"] = record.request_id

        extra_str = f" [{extra_info}]" if extra_info else ""
        return f"[{timestamp}] [{level:<8}] [{name}]: {message}{extra_str}"


def setup_logging(log_level: str = "INFO") -> None:
    """Configures application-wide logging."""
    root_logger = logging.getLogger()
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    root_logger.setLevel(numeric_level)

    # Avoid duplicate handlers if re-run
    if not root_logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            StructuredFormatter(datefmt="%Y-%m-%d %H:%M:%S")
        )
        root_logger.addHandler(handler)
    else:
        for handler in root_logger.handlers:
            handler.setFormatter(
                StructuredFormatter(datefmt="%Y-%m-%d %H:%M:%S")
            )


logger = logging.getLogger("docforge")
