"""
Centralized logging configuration for the backend.

Ensures that Loguru writes to both the console and the shared log file, and
bridges standard `logging` (used by uvicorn/reloader) into Loguru so every log
message ends up in the same sinks across processes.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Optional

from loguru import logger

LOG_FILE = Path(__file__).resolve().parents[2] / "logs" / "backend.log"
_configured = False


class _InterceptHandler(logging.Handler):
    """Redirect standard logging records to Loguru."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def _setup_stdlib_interception() -> None:
    """Route stdlib logging (incl. uvicorn) through Loguru sinks."""
    intercept_handler = _InterceptHandler()
    logging.root.handlers = [intercept_handler]
    logging.root.setLevel(logging.NOTSET)

    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access", "uvicorn.asgi", "uvicorn.lifespan"):
        std_logger = logging.getLogger(logger_name)
        std_logger.handlers = [intercept_handler]
        std_logger.setLevel(logging.INFO)
        std_logger.propagate = False


def setup_logging(
    *,
    enable_console: bool = True,
    console_colorize: Optional[bool] = None,
    intercept_stdlib: bool = True,
) -> None:
    """
    Configure Loguru sinks and (optionally) stdlib interception.

    Idempotent per-process: multiple calls will no-op after the first.
    """
    global _configured
    if _configured:
        return

    logger.remove()

    if enable_console:
        colorize = console_colorize if console_colorize is not None else sys.stderr.isatty()
        logger.add(
            sys.stderr,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            level="INFO",
            colorize=colorize,
        )

    LOG_FILE.parent.mkdir(exist_ok=True, parents=True)
    logger.add(
        str(LOG_FILE),
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="DEBUG",
        rotation="10 MB",
        retention="7 days",
        enqueue=True,  # Safe when uvicorn reload/workers spawn new processes.
    )

    if intercept_stdlib:
        _setup_stdlib_interception()

    _configured = True


