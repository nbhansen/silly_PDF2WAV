# app.py - Lean main entry point (refactored from 739 lines)
import os
import signal
import sys
import atexit
from typing import Optional
from dotenv import load_dotenv

from app_factory import create_app
from application.composition_root import create_pdf_service_from_env
from application.config.system_config import SystemConfig
from infrastructure.file.cleanup_scheduler import FileCleanupScheduler

# Load environment variables first
load_dotenv()

# Initialize configuration
app_config = SystemConfig.from_env()

# Create Flask app
app = create_app()

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
            pdf_service = create_pdf_service_from_env()
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


def signal_handler(sig, frame):
    print(f"\nReceived signal {sig}, shutting down gracefully...")
    if not is_flask_reloader():
        shutdown_cleanup()
    sys.exit(0)


# Initialize services
initialize_services()

# Register routes
from routes import register_routes
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
        app.run(debug=True, host='0.0.0.0', port=5000)
    finally:
        # Only cleanup in main process
        if not is_flask_reloader():
            shutdown_cleanup()