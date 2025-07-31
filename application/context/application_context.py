"""Application context for dependency injection and global state elimination.

This module provides the ApplicationContext class which encapsulates all application-wide
dependencies and eliminates global state, following hexagonal architecture principles.
"""

from dataclasses import dataclass
import logging
from typing import Any, Optional, Protocol

from application.config.system_config import SystemConfig
from domain.container.service_container import ServiceContainer
from infrastructure.file.cleanup_scheduler import FileCleanupScheduler


class LoggerFactory(Protocol):
    """Protocol for logger factory to avoid circular imports."""

    def get_logger(self, name: str) -> logging.Logger:
        """Get a logger for the specified module."""
        ...

    def get_app_logger(self) -> logging.Logger:
        """Get the main application logger."""
        ...


@dataclass(frozen=True)
class ApplicationContext:
    """Immutable application context that encapsulates all application-wide dependencies.

    This eliminates global state by providing a single, thread-safe container
    for all application services and configuration.
    """

    config: SystemConfig
    service_container: ServiceContainer
    logger_factory: LoggerFactory
    cleanup_scheduler: Optional[FileCleanupScheduler] = None

    @property
    def is_processor_available(self) -> bool:
        """Check if PDF processing service is available."""
        try:
            # Check if we can get an audio engine (main processing component)
            from domain.audio.audio_engine import IAudioEngine

            audio_service = self.service_container.get(IAudioEngine)
            return audio_service is not None
        except Exception:
            return False

    @property
    def pdf_service(self) -> Any:
        """Get PDF processing service (audio engine)."""
        from domain.audio.audio_engine import IAudioEngine

        return self.service_container.get(IAudioEngine)

    def get_logger(self, name: str) -> logging.Logger:
        """Get a logger instance for the given module."""
        return self.logger_factory.get_logger(name)
