# app_factory.py - Minimal Flask app creation and setup
from pathlib import Path
from typing import Any

from flask import Flask

from application.config.system_config import SystemConfig


def create_app(app_config: SystemConfig) -> Flask:
    """Create and configure Flask application."""
    app = Flask(__name__)

    # Configure Flask app
    app.config["UPLOAD_FOLDER"] = app_config.upload_folder
    app.config["AUDIO_FOLDER"] = app_config.audio_folder
    app.config["MAX_CONTENT_LENGTH"] = app_config.max_file_size_mb * 1024 * 1024

    # Create directories
    Path(app_config.upload_folder).mkdir(parents=True, exist_ok=True)
    Path(app_config.audio_folder).mkdir(parents=True, exist_ok=True)

    # Register error handlers
    @app.errorhandler(413)
    def too_large(e: Any) -> tuple[str, int]:
        return f"File is too large. Maximum file size is {app_config.max_file_size_mb}MB.", 413

    @app.errorhandler(Exception)
    def handle_exception(e: Exception) -> tuple[str, int]:
        import traceback

        print("🚨 FULL ERROR TRACEBACK:")
        print(traceback.format_exc())
        print(f"🚨 Exception type: {type(e)}")
        print(f"🚨 Exception message: {e!s}")
        return f"An error occurred: {e!s}", 500

    return app
