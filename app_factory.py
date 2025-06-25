# app_factory.py - Minimal Flask app creation and setup
import os
from flask import Flask
from application.config.system_config import SystemConfig


def create_app(app_config: SystemConfig = None):
    """Create and configure Flask application"""
    app = Flask(__name__)
    
    # Load configuration if not provided
    if app_config is None:
        app_config = SystemConfig.from_env()
    
    # Configure Flask app
    app.config['UPLOAD_FOLDER'] = app_config.upload_folder
    app.config['AUDIO_FOLDER'] = app_config.audio_folder
    app.config['MAX_CONTENT_LENGTH'] = app_config.max_file_size_mb * 1024 * 1024

    # Create directories
    os.makedirs(app_config.upload_folder, exist_ok=True)
    os.makedirs(app_config.audio_folder, exist_ok=True)

    # Register error handlers
    @app.errorhandler(413)
    def too_large(e):
        return f"File is too large. Maximum file size is {app_config.max_file_size_mb}MB.", 413

    @app.errorhandler(Exception)
    def handle_exception(e):
        import traceback
        print(f"🚨 FULL ERROR TRACEBACK:")
        print(traceback.format_exc())
        print(f"🚨 Exception type: {type(e)}")
        print(f"🚨 Exception message: {str(e)}")
        return f"An error occurred: {str(e)}", 500

    return app