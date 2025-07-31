# application/config/logging_config.py
from dataclasses import dataclass
import datetime
import json
import logging
import logging.handlers
from pathlib import Path
import sys
from typing import Optional


@dataclass(frozen=True)
class LoggingConfig:
    """Configuration for application logging system."""

    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_path: Optional[str] = None
    json_format: bool = False
    max_file_size_mb: int = 10
    backup_count: int = 5
    console_output: bool = True

    def __post_init__(self) -> None:
        """Validate logging configuration."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if self.level.upper() not in valid_levels:
            raise ValueError(f"Invalid log level: {self.level}. Must be one of {valid_levels}")

        if self.max_file_size_mb <= 0:
            raise ValueError("max_file_size_mb must be positive")

        if self.backup_count < 0:
            raise ValueError("backup_count cannot be negative")


def setup_logging(config: LoggingConfig) -> logging.Logger:
    """Set up application logging with the given configuration.

    Args:
        config: Logging configuration

    Returns:
        Configured logger instance
    """
    # Get root logger for the application
    logger = logging.getLogger("pdf_to_audio")

    # Clear any existing handlers to avoid duplication
    logger.handlers.clear()

    # Set logging level
    logger.setLevel(getattr(logging, config.level.upper()))

    # Create formatter
    if config.json_format:
        # JSON formatter for structured logging

        class JSONFormatter(logging.Formatter):
            def format(self, record: logging.LogRecord) -> str:
                log_entry = {
                    "timestamp": datetime.datetime.fromtimestamp(record.created).isoformat(),
                    "level": record.levelname,
                    "logger": record.name,
                    "message": record.getMessage(),
                    "module": record.module,
                    "function": record.funcName,
                    "line": record.lineno,
                }

                if record.exc_info:
                    log_entry["exception"] = self.formatException(record.exc_info)

                return json.dumps(log_entry)

        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(config.format)

    # Console handler
    if config.console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    # File handler (if file path specified)
    if config.file_path:
        # Ensure directory exists
        log_file = Path(config.file_path)
        log_file.parent.mkdir(parents=True, exist_ok=True)

        # Use rotating file handler to prevent huge log files
        file_handler = logging.handlers.RotatingFileHandler(
            config.file_path, maxBytes=config.max_file_size_mb * 1024 * 1024, backupCount=config.backup_count
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    # Prevent propagation to root logger to avoid duplicate messages
    logger.propagate = False

    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger for a specific module.

    Args:
        name: Module name (typically __name__)

    Returns:
        Logger instance for the module
    """
    return logging.getLogger(f"pdf_to_audio.{name}")


# Global logger instance - will be configured by the application
_app_logger: Optional[logging.Logger] = None


def configure_application_logging(config: LoggingConfig) -> None:
    """Configure application-wide logging.

    Args:
        config: Logging configuration
    """
    global _app_logger
    _app_logger = setup_logging(config)


def get_app_logger() -> logging.Logger:
    """Get the main application logger.

    Returns:
        Main application logger

    Raises:
        RuntimeError: If logging has not been configured
    """
    if _app_logger is None:
        # Fallback configuration for development
        fallback_config = LoggingConfig()
        configure_application_logging(fallback_config)

    return _app_logger
