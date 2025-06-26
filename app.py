# app.py - Lean main entry point
import os
import signal
import sys
import atexit
from typing import Optional

from app_factory import create_app
from domain.factories.service_factory import create_pdf_service_from_env
from application.config.system_config import SystemConfig
from infrastructure.file.cleanup_scheduler import FileCleanupScheduler


# Initialize configuration - prefer YAML, fallback to env vars
try:
    app_config = SystemConfig.from_yaml()
    print("✅ Loaded configuration from config.yaml")
except FileNotFoundError:
    print("⚠️  config.yaml not found, copy config.example.yaml to config.yaml and edit that")

# Create Flask app with our config
app = create_app(app_config)

# Global services
pdf_service = None
processor_available = False
cleanup_scheduler: Optional[FileCleanupScheduler] = None


def is_flask_reloader():
    """Check if we're in Flask debug reloader process"""
    return os.environ.get('WERKZEUG_RUN_MAIN') != 'true'


def initialize_services():
    """Initialize PDF processing service - ONLY in main process"""
    global pdf_service, processor_available
    
    if not is_flask_reloader():
        print("Initializing PDF Processing Service...")
        try:
            pdf_service = create_pdf_service_from_env(app_config)
            print("PDF Processing Service initialized successfully")
            processor_available = True
        except Exception as e:
            print(f"CRITICAL: PDF Service initialization failed: {e}")
            pdf_service = None
            processor_available = False
    else:
        print("⚡ Skipping initialization in Flask reloader process")


def shutdown_cleanup():
    """Clean shutdown with proper cleanup scheduler stop"""
    global cleanup_scheduler
    if cleanup_scheduler:
        print("Shutting down file cleanup scheduler...")
        cleanup_scheduler.stop()


def signal_handler(sig, _frame):
    print(f"\nReceived signal {sig}, shutting down gracefully...")
    if not is_flask_reloader():
        shutdown_cleanup()
    sys.exit(0)


# Initialize services
initialize_services()

# Register routes and share services + config
from routes import register_routes, set_services
set_services(pdf_service, processor_available, app_config)
register_routes(app)

# Register shutdown handlers
atexit.register(lambda: shutdown_cleanup() if not is_flask_reloader() else None)
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

if __name__ == '__main__':
    # Only print startup info once
    if not is_flask_reloader():
        print("Starting Flask development server...")
        print(f"TTS Engine: {app_config.tts_engine.value}")
        print(f"Text Cleaning: {'Enabled' if app_config.enable_text_cleaning else 'Disabled'}")
        print(f"File Cleanup: {'Enabled' if app_config.enable_file_cleanup else 'Disabled'}")

    try:
        app.run(
            debug=app_config.flask_debug,
            host=app_config.flask_host,
            port=app_config.flask_port
        )
    finally:
        # Only cleanup in main process
        if not is_flask_reloader():
            shutdown_cleanup()