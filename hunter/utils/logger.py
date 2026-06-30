"""
logger.py — Centralised logging configuration for Treasure Hunter AI.

Call ``setup_logging()`` once at startup (from ``main.py``).
All other modules obtain their logger via ``logging.getLogger(__name__)``.
"""

from __future__ import annotations

import logging
import logging.handlers
import os
import sys
from typing import Optional

from config.settings import LOG_FILE, LOG_LEVEL


def setup_logging(
    level: Optional[str] = None,
    log_file: Optional[str] = None,
    *,
    console: bool = True,
) -> None:
    """Configure root logger with console and rotating-file handlers.

    Args:
        level:    Override the log level (default: ``LOG_LEVEL`` from settings).
        log_file: Override the log file path (default: ``LOG_FILE`` from settings).
        console:  Whether to attach a ``StreamHandler`` to stdout.
    """
    resolved_level: str = (level or LOG_LEVEL).upper()
    resolved_file: str = log_file or LOG_FILE

    root = logging.getLogger()
    root.setLevel(resolved_level)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)-30s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    if console:
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setLevel(resolved_level)
        stream_handler.setFormatter(formatter)
        root.addHandler(stream_handler)

    # Rotating file handler (max 5 MB × 3 backups)
    try:
        os.makedirs(os.path.dirname(resolved_file), exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            resolved_file,
            maxBytes=5 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        )
        file_handler.setLevel(resolved_level)
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)
    except OSError as exc:
        logging.warning("Could not create log file %s: %s", resolved_file, exc)


def get_logger(name: str) -> logging.Logger:
    """Convenience wrapper — identical to ``logging.getLogger(name)``."""
    return logging.getLogger(name)
