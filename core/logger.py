"""Structured logging configuration using Loguru."""

import sys
from pathlib import Path
from loguru import logger
from core.config import settings

# Ensure log directory exists
LOGS_DIR = Path("logs")
LOGS_DIR.mkdir(exist_ok=True)

# Remove default logger handlers
logger.remove()

# Console logger with clean formatting
logger.add(
    sys.stdout,
    level=settings.LOG_LEVEL,
    format=(
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    ),
    colorize=True,
    enqueue=True,
)

# File logger with rotation & retention
logger.add(
    LOGS_DIR / "warden_{time:YYYY-MM-DD}.log",
    level="DEBUG",
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
    rotation="00:00",
    retention="14 days",
    compression="zip",
    enqueue=True,
    encoding="utf-8",
)

__all__ = ["logger"]
