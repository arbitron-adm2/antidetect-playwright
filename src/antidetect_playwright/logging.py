"""Logging setup."""

import logging
import logging.handlers
import sys
from pathlib import Path

from .config import LoggingConfig


def setup_logging(config: LoggingConfig, logs_dir: str) -> None:
    """Configure application logging.

    Args:
        config: Logging configuration.
        logs_dir: Directory for log files.
    """
    logs_path = Path(logs_dir)
    logs_path.mkdir(parents=True, exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, config.level.upper()))

    root_logger.handlers.clear()

    formatter = logging.Formatter(
        fmt=config.format,
        datefmt=config.date_format,
    )

    if config.console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    if config.file:
        log_file = logs_path / "app.log"
        file_handler = logging.handlers.RotatingFileHandler(
            filename=log_file,
            maxBytes=config.max_size_mb * 1024 * 1024,
            backupCount=config.backup_count,
        )
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    logging.getLogger("playwright").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get logger for module.

    Args:
        name: Logger name, typically __name__.

    Returns:
        Configured logger instance.
    """
    return logging.getLogger(name)
