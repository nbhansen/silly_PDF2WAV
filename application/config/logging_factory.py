"""Thread-safe logger factory for managing logger instances.

This module provides a thread-safe logger factory that manages logger instances
without using global state, supporting the hexagonal architecture pattern.
"""

import logging
import logging.handlers
from threading import RLock
from typing import Optional

from application.config.logging_config import LoggingConfig, setup_logging


class ThreadSafeLoggerFactory:
    """Thread-safe logger factory that manages logger instances."""

    def __init__(self, config: LoggingConfig):
        """Initialize logger factory with logging configuration.

        Args:
            config: Logging configuration to use for all loggers
        """
        self._config = config
        self._lock = RLock()
        self._loggers: dict[str, logging.Logger] = {}
        self._app_logger: Optional[logging.Logger] = None

        # Initialize main application logger
        with self._lock:
            self._app_logger = setup_logging(config)

    def get_logger(self, name: str) -> logging.Logger:
        """Get or create a logger for the given module name.

        Args:
            name: Module name for the logger

        Returns:
            Logger instance for the module
        """
        with self._lock:
            if name not in self._loggers:
                if name == "__main__" or name == "app":
                    if self._app_logger is None:
                        raise RuntimeError("Application logger not initialized")
                    return self._app_logger

                # Create module-specific logger
                logger_name = f"pdf_to_audio.{name}"
                self._loggers[name] = logging.getLogger(logger_name)

            return self._loggers[name]

    def get_app_logger(self) -> logging.Logger:
        """Get the main application logger.

        Returns:
            Main application logger instance
        """
        if self._app_logger is None:
            raise RuntimeError("Application logger not initialized")
        return self._app_logger
