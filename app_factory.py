"""Flask application factory with proper dependency injection.

This module provides the Flask application factory that creates and configures
the Flask app with all dependencies properly injected, eliminating global state.
"""

from pathlib import Path
from typing import Optional

from flask import Flask

from application.config.logging_config import LoggingConfig
from application.config.logging_factory import ThreadSafeLoggerFactory
from application.config.system_config import SystemConfig
from application.container.service_container import ServiceContainer
from application.context.application_context import ApplicationContext
from infrastructure.file.cleanup_scheduler import FileCleanupScheduler


def create_service_container(config: SystemConfig, logger_factory: ThreadSafeLoggerFactory) -> ServiceContainer:
    """Create service container with all dependencies."""
    logger = logger_factory.get_logger("service_factory")

    # Create container - it builds all services automatically
    container = ServiceContainer(config)

    logger.info("Service container initialized successfully")
    return container


def create_app(config_path: Optional[Path] = None) -> Flask:
    """Create and configure Flask application with proper dependency injection.

    This factory function ensures no global state by creating all dependencies
    within the factory scope and injecting them into the Flask app.

    Args:
        config_path: Optional path to configuration file

    Returns:
        Configured Flask application
    """
    # Load configuration
    if config_path and config_path.exists():
        app_config = SystemConfig.from_yaml(str(config_path))
    else:
        app_config = SystemConfig.from_yaml()

    # Create logger factory (no global state) with file logging for home user debugging
    log_dir = Path.home() / ".pdf_to_audio"
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / "app.log"

    logging_config = LoggingConfig(level="INFO", console_output=True, file_path=str(log_file))
    logger_factory = ThreadSafeLoggerFactory(logging_config)
    logger = logger_factory.get_logger(__name__)

    # Create service container
    logger.info("Initializing services...")
    service_container = create_service_container(app_config, logger_factory)

    # Create cleanup scheduler if enabled
    cleanup_scheduler = None
    if app_config.cleanup.enabled:
        from domain.interfaces import IFileManager

        file_manager = service_container.get(IFileManager)
        cleanup_scheduler = FileCleanupScheduler(
            file_manager=file_manager,
            max_file_age_seconds=int(app_config.cleanup.max_file_age_hours * 3600),
            check_interval_seconds=300,
        )

    # Create application context
    app_context = ApplicationContext(
        config=app_config,
        service_container=service_container,
        logger_factory=logger_factory,
        cleanup_scheduler=cleanup_scheduler,
    )

    # Create Flask app
    app = Flask(__name__)

    # Configure Flask
    app.config["UPLOAD_FOLDER"] = app_config.files.upload_folder
    app.config["AUDIO_FOLDER"] = app_config.files.audio_folder
    app.config["MAX_CONTENT_LENGTH"] = app_config.files.max_file_size_mb * 1024 * 1024

    # Inject application context (no global state!)
    app.config["APP_CONTEXT"] = app_context

    # Create directories
    Path(app_config.files.upload_folder).mkdir(parents=True, exist_ok=True)
    Path(app_config.files.audio_folder).mkdir(parents=True, exist_ok=True)

    # Register error handlers
    register_error_handlers(app, app_context)

    logger.info("Flask application created successfully")
    return app


def register_error_handlers(app: Flask, context: ApplicationContext) -> None:
    """Register error handlers with access to application context."""
    logger = context.get_logger("error_handlers")

    @app.errorhandler(413)
    def too_large(e: object) -> tuple[str, int]:
        max_size = context.config.files.max_file_size_mb
        return f"File is too large. Maximum file size is {max_size}MB.", 413

    @app.errorhandler(Exception)
    def handle_exception(e: Exception) -> tuple[str, int]:
        import traceback

        logger.error("Unhandled exception occurred")
        logger.error("Full traceback: %s", traceback.format_exc())
        logger.error("Exception type: %s", type(e).__name__)
        logger.error("Exception message: %s", str(e))
        return f"An error occurred: {e!s}", 500
