"""Flask route handlers with proper dependency injection.

This module provides all route handlers that use ApplicationContext for
dependency injection, eliminating global state.
"""

import contextlib
import json
import logging
import os
from pathlib import Path
import threading
import time
from typing import Any, Optional, Union
import uuid

from flask import Flask, Response, current_app, jsonify, render_template, request, send_from_directory, url_for
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from application.config.system_config import SystemConfig
from application.container.service_container import ServiceContainer
from application.context.application_context import ApplicationContext
from application.services.document_service import DocumentProcessingService
from application.services.error_formatting import (
    get_contextual_error_message,
    get_processing_stage_error,
)
from application.services.progress_store import (
    cancel_operation,
    get_progress,
    update_progress,
)
from domain.models import PageRange, ProcessingResult
from infrastructure.file.file_manager import FileManager
from utils import (
    allowed_file,
)


def background_process_document(
    operation_id: str,
    request_form: dict,
    saved_file_path: str,
    original_filename: str,
    enable_timing: bool,
    app_context: ApplicationContext,
    app: Flask,
) -> None:
    """Background processing function that delegates to DocumentProcessingService.

    Args:
        operation_id: Unique ID for this operation
        request_form: Form data as dict
        saved_file_path: Path where the uploaded file was saved
        original_filename: Original filename from upload
        enable_timing: Whether to enable timing data
        app_context: Application context
        app: Flask app instance
    """
    # Use the Flask app context for this thread
    with app.app_context():
        # Store context in Flask app for access in helper functions if needed
        app.config["APP_CONTEXT"] = app_context

        try:
            # Get service from container
            service = app_context.service_container.get(DocumentProcessingService)

            # Delegate all orchestration logic to service
            service.process_document_background(
                operation_id=operation_id,
                request_form=request_form,
                saved_file_path=saved_file_path,
                original_filename=original_filename,
                enable_timing=enable_timing,
            )

        except Exception as e:
            get_logger("routes").exception(f"Background process wrapper failed: {e}")
            enhanced_error = get_processing_stage_error("processing", e, original_filename)
            update_progress(
                operation_id, "error", 0, "Processing failed unexpectedly", is_error=True, error_message=enhanced_error
            )


def get_app_context() -> ApplicationContext:
    """Get application context from Flask app context."""
    return current_app.config["APP_CONTEXT"]  # type: ignore[no-any-return]


def get_pdf_service() -> ServiceContainer:
    """Get PDF service from context."""
    return get_app_context().service_container


def is_processor_available() -> bool:
    """Check if processor is available from context."""
    try:
        result = get_app_context().is_processor_available
        logger = get_logger("routes")
        logger.info(f"Processor available check: {result}")
        return result
    except Exception as e:
        logger = get_logger("routes")
        logger.error(f"Error checking processor availability: {e}")
        return False


def get_app_config() -> SystemConfig:
    """Get app config from context."""
    return get_app_context().config


def get_logger(name: str) -> logging.Logger:
    """Get logger from context."""
    return get_app_context().get_logger(name)


def register_routes(app: Flask) -> None:
    """Register all routes with the Flask app."""

    @app.route("/")
    def index() -> str:
        context = get_app_context()
        return render_template("index.html", tts_engine=context.config.tts.engine.value)

    @app.route("/favicon.ico")
    def favicon() -> tuple[str, int]:
        """Return a simple response for favicon requests to avoid 404 errors."""
        return "", 204

    @app.route("/audio_outputs/<filename>")
    def serve_audio(filename: str) -> Response:
        return send_from_directory(app.config["AUDIO_FOLDER"], filename)

    @app.route("/read-along/<filename>")
    def read_along_view(filename: str) -> Union[str, tuple[str, int]]:
        """Serve read-along interface for audio file."""
        # Extract base filename (remove extension and _combined suffix)
        base_filename = filename.replace("_combined.mp3", "").replace(".mp3", "").replace(".wav", "")

        # Check if timing data exists
        timing_filename = f"{base_filename}_timing.json"
        timing_path = Path(app.config["AUDIO_FOLDER"]) / timing_filename

        if not timing_path.exists():
            return f"Timing data not found for {filename}. This file was not processed with read-along support.", 404

        # Check if audio file exists
        audio_path = Path(app.config["AUDIO_FOLDER"]) / filename
        if not audio_path.exists():
            return f"Audio file {filename} not found.", 404

        # Load timing data for template rendering
        import json

        try:
            with timing_path.open() as f:
                timing_json = json.load(f)
                timing_segments = timing_json.get("text_segments", [])
        except Exception as e:
            return f"Error loading timing data: {e}", 500

        return render_template(
            "read_along.html",
            audio_filename=filename,
            base_filename=base_filename,
            timing_data=timing_segments,
            timing_api_url=url_for("get_timing_data", filename=base_filename),
        )

    @app.route("/api/timing/<filename>")
    def get_timing_data(filename: str) -> Union[Response, tuple[Response, int]]:
        """Serve timing metadata as JSON."""
        timing_filename = f"{filename}_timing.json"
        timing_path = Path(app.config["AUDIO_FOLDER"]) / timing_filename

        if not timing_path.exists():
            return jsonify({"error": "Timing data not found"}), 404

        try:
            with timing_path.open(encoding="utf-8") as f:
                timing_data = json.load(f)

            return jsonify(timing_data)
        except Exception as e:
            get_logger("routes").error("Error serving timing data: %s", str(e))
            return jsonify({"error": "Failed to load timing data"}), 500

    @app.route("/api/progress/<operation_id>")
    def get_progress_status(operation_id: str) -> Union[Response, tuple[Response, int]]:
        """Get current progress status for an operation."""
        progress = get_progress(operation_id)
        if progress is None:
            return jsonify({"error": "Operation not found"}), 404

        return jsonify(
            {
                "operation_id": progress.operation_id,
                "stage": progress.stage,
                "percentage": progress.percentage,
                "message": progress.message,
                "complete": progress.is_complete,
                "error": progress.is_error,
                "error_message": progress.error_message,
                "cancelled": progress.cancelled,
                "result_data": progress.result_data,
            }
        )

    @app.route("/api/cancel/<operation_id>", methods=["POST"])
    def cancel_processing_operation(operation_id: str) -> Union[Response, tuple[Response, int]]:
        """Cancel a running operation."""
        progress = get_progress(operation_id)
        if progress is None:
            return jsonify({"error": "Operation not found"}), 404

        if progress.is_complete:
            return jsonify({"message": "Operation already completed", "cancelled": False}), 200

        cancel_operation(operation_id)
        return jsonify({"message": "Cancellation requested", "cancelled": True})

    @app.route("/result/<operation_id>")
    def show_result(operation_id: str) -> Union[str, tuple[str, int]]:
        """Show results for a completed operation."""
        progress = get_progress(operation_id)
        if progress is None:
            return "Operation not found", 404

        if not progress.is_complete:
            return "Operation not yet complete", 400

        if progress.is_error or progress.error_message:
            return f"Processing failed: {progress.error_message or 'Unknown error'}", 500

        if progress.cancelled:
            return "Operation was cancelled", 400

        if not progress.result_data:
            return "No result data available", 500

        # Extract result data
        result_data = progress.result_data
        base_filename = result_data.get("base_filename", "unknown")
        original_filename = result_data.get("original_filename", "unknown")
        processing_result = result_data.get("processing_result")

        if not processing_result:
            return "No processing result available", 500

        # We need to reconstruct the page range - for now use default
        from domain.models import PageRange

        page_range = PageRange(start_page=None, end_page=None)  # Default to all pages

        # Check if this was a timing-enabled operation
        enable_timing = progress.stage in ["complete"] and processing_result.timing_data is not None

        # Render the result using the existing function
        return render_upload_result(processing_result, original_filename, base_filename, page_range, enable_timing)

    @app.route("/get_pdf_info", methods=["POST"])
    def get_pdf_info() -> Union[Response, tuple[Response, int]]:
        service = get_pdf_service()
        if not is_processor_available() or service is None:
            return (
                jsonify(
                    {
                        "error": "PDF processing service is not available. Please check system "
                        "configuration and try again."
                    }
                ),
                500,
            )

        if "pdf_file" not in request.files:
            return jsonify({"error": "No file was uploaded. Please select a PDF file and try again."}), 400

        file = request.files["pdf_file"]
        if not file.filename or file.filename == "" or not allowed_file(file.filename):
            filename = getattr(file, "filename", "unknown")
            return jsonify({"error": f"Invalid file '{filename}'. Only PDF files are supported for processing."}), 400

        try:
            # Save temporary file
            original_filename = secure_filename(file.filename)
            temp_path = Path(app.config["UPLOAD_FOLDER"]) / f"temp_{original_filename}"
            file.save(str(temp_path))

            # Use document engine to get PDF info
            from domain.interfaces import IDocumentEngine

            document_engine = service.get(IDocumentEngine)
            pdf_info_result = document_engine.get_pdf_info(str(temp_path))

            # Clean up
            with contextlib.suppress(Exception):
                temp_path.unlink()

            if pdf_info_result.is_success:
                pdf_info = pdf_info_result.value
                assert pdf_info is not None  # Type hint for mypy
                return jsonify(
                    {"total_pages": pdf_info.total_pages, "title": pdf_info.title, "author": pdf_info.author}
                )
            else:
                return jsonify({"error": f"Failed to analyze PDF '{original_filename}': {pdf_info_result.error}"}), 500

        except Exception as e:
            return jsonify({"error": f"Unexpected error while analyzing PDF: {e!s}"}), 500

    def _validate_upload_request() -> tuple[Optional[FileStorage], Optional[str]]:
        """Common validation for upload endpoints.

        Returns:
            (file, error_message) - file if valid, error message if invalid
        """
        service = get_pdf_service()
        if not is_processor_available() or service is None:
            return (
                None,
                "PDF processing service is temporarily unavailable. Please check your "
                "configuration and try again in a few moments.",
            )

        if "pdf_file" not in request.files:
            return None, "No file was uploaded. Please select a PDF file and try again."

        file = request.files["pdf_file"]
        if not file.filename or file.filename == "":
            return None, "No file was selected. Please choose a PDF file to upload."
        elif not allowed_file(file.filename):
            return None, f"File '{file.filename}' is not a PDF. Only PDF files are supported for audio conversion."

        return file, None

    def _handle_upload(enable_timing: bool) -> Union[str, tuple[str, int]]:
        """Shared upload handler for both regular and timing-enabled uploads.

        Args:
            enable_timing: Whether to enable timing data for read-along functionality.
        """
        file, error = _validate_upload_request()
        if error or file is None:
            return error or "No file provided"

        # Generate unique operation ID
        operation_id = str(uuid.uuid4())

        # Initialize progress tracking
        timing_suffix = " with timing data" if enable_timing else ""
        update_progress(operation_id, "starting", 0, f"Upload received, starting processing{timing_suffix}...")

        # Save file first before passing to thread (FileStorage closes after request)
        config = get_app_config()
        if not file.filename:
            return "No filename provided", 400
        original_filename = secure_filename(file.filename)
        saved_path = Path(config.files.upload_folder) / f"{operation_id}_{original_filename}"
        file.save(str(saved_path))

        # Convert form data to dict (Flask objects don't work in threads)
        form_data = dict(request.form)

        # Start background processing with app context
        from flask import current_app

        thread = threading.Thread(
            target=background_process_document,
            args=(
                operation_id,
                form_data,
                str(saved_path),
                original_filename,
                enable_timing,
                get_app_context(),
                current_app._get_current_object(),
            ),
            daemon=True,
        )
        thread.start()

        # Return processing page immediately
        return render_template("processing.html", operation_id=operation_id, enable_timing=enable_timing)

    @app.route("/upload", methods=["POST"])
    def upload_file() -> Union[str, tuple[str, int]]:
        """Regular upload WITHOUT timing data."""
        return _handle_upload(enable_timing=False)

    @app.route("/upload-with-timing", methods=["POST"])
    def upload_file_with_timing() -> Union[str, tuple[str, int]]:
        """Upload WITH timing data for read-along functionality."""
        config = get_app_config()
        if config.tts.engine.value == "gemini":
            return "Read-along mode is not available with Gemini TTS. Please use regular upload or switch to Piper TTS."
        return _handle_upload(enable_timing=True)

    @app.route("/admin/file_stats")
    def get_file_stats() -> Union[Response, tuple[Response, int]]:
        """Get file management statistics (admin endpoint)."""
        service = get_pdf_service()
        if not is_processor_available():
            return jsonify({"error": "Service not available"}), 500

        try:
            if not service.has(FileManager):
                return jsonify({"error": "File management not available"}), 404

            audio_dir = Path(app.config["AUDIO_FOLDER"])
            if not audio_dir.exists():
                return jsonify({"error": "Audio directory not found"}), 404

            files = list(audio_dir.iterdir())
            total_size = sum(f.stat().st_size for f in files if f.is_file())

            stats = {
                "total_files": len(files),
                "total_size_mb": total_size / (1024 * 1024),
                "directory": str(audio_dir),
                "cleanup_enabled": get_app_config().enable_file_cleanup,
            }
            return jsonify(stats)

        except Exception as e:
            get_logger("routes").error("Admin file_stats error: %s", str(e))
            return jsonify({"error": str(e)}), 500

    @app.route("/admin/cleanup", methods=["POST"])
    def manual_cleanup() -> Union[Response, tuple[Response, int]]:
        """Trigger manual file cleanup (admin endpoint)."""
        service = get_pdf_service()
        if not is_processor_available():
            return jsonify({"error": "Service not available"}), 500

        try:
            if not service.has(FileManager):
                return jsonify({"error": "File management not available"}), 404

            max_age_hours = float(request.form.get("max_age_hours", 24.0))
            audio_dir = Path(app.config["AUDIO_FOLDER"])
            cutoff_time = time.time() - (max_age_hours * 3600)

            removed_files = 0
            bytes_freed = 0
            errors: list[str] = []

            for filepath in audio_dir.iterdir():
                if filepath.is_file() and filepath.stat().st_mtime < cutoff_time:
                    try:
                        file_size = filepath.stat().st_size
                        filepath.unlink()
                        removed_files += 1
                        bytes_freed += file_size
                        get_logger("routes").info("Cleaned up old file: %s", filepath.name)
                    except Exception as e:
                        errors.append(f"Failed to remove {filepath.name}: {e!s}")

            result = {
                "files_removed": removed_files,
                "bytes_freed": bytes_freed,
                "mb_freed": bytes_freed / (1024 * 1024),
                "errors": errors,
                "max_age_hours": max_age_hours,
            }
            return jsonify(result)

        except Exception as e:
            get_logger("routes").error("Admin cleanup error: %s", str(e))
            return jsonify({"error": str(e)}), 500

    @app.route("/admin/cleanup_scheduler", methods=["POST"])
    def trigger_scheduler_cleanup() -> Union[Response, tuple[Response, int]]:
        """Trigger scheduler's manual cleanup."""
        try:
            context = get_app_context()
            scheduler = context.cleanup_scheduler

            if scheduler is None:
                return jsonify({"error": "Cleanup scheduler not available"}), 500

            if hasattr(scheduler, "run_manual_cleanup"):
                result = scheduler.run_manual_cleanup()
                return jsonify(result)
            else:
                return jsonify({"error": "Manual cleanup not supported by scheduler"}), 404

        except Exception as e:
            get_logger("routes").error("Scheduler cleanup error: %s", str(e))
            return jsonify({"error": str(e)}), 500

    @app.route("/admin/test")
    def test_admin() -> Union[Response, tuple[Response, int]]:
        """Test endpoint to check what's available."""
        try:
            service = get_pdf_service()

            def is_flask_reloader() -> bool:
                return os.environ.get("WERKZEUG_RUN_MAIN") != "true"

            has_file_manager = service.has(FileManager)

            info: dict[str, Any] = {
                "processor_available": is_processor_available(),
                "service_exists": True,
                "has_file_manager": has_file_manager,
                "service_type": service.__class__.__name__,
                "file_cleanup_enabled": get_app_config().enable_file_cleanup,
                "is_reloader_process": is_flask_reloader(),
            }

            if has_file_manager:
                file_manager = service.get(FileManager)
                info["file_manager_type"] = file_manager.__class__.__name__

            return jsonify(info)

        except Exception as e:
            return jsonify({"error": str(e)}), 500


def render_upload_result(
    result: Optional[ProcessingResult],
    original_filename: str,
    base_filename_no_ext: str,
    page_range: PageRange,
    enable_timing: bool = False,
) -> str:
    """Render the result template with appropriate parameters."""
    if result is None:
        return render_template("error.html", error_message="Processing failed - no result returned")

    get_logger("routes").debug("DEBUG: result.success=%s, result.error=%s", result.success, result.error)
    if result.success:
        display_filename = original_filename
        if not page_range.is_full_document():
            display_filename += f" (pages {page_range.start_page or 1}-{page_range.end_page or 'end'})"

        # CRITICAL: Different template parameters based on timing
        template_params = {
            "audio_files": result.audio_files or [],
            "combined_mp3_file": result.combined_mp3_file,
            "original_filename": display_filename,
            "tts_engine": get_app_config().tts.engine.value,
            "file_count": len(result.audio_files) if result.audio_files else 0,
            "debug_info": result.debug_info,
        }

        # Add timing-specific parameters for read-along functionality
        if enable_timing:
            template_params.update(
                {
                    "has_timing_data": True,  # Enables read-along button
                    "base_filename": base_filename_no_ext,  # For read-along URL
                }
            )
            get_logger("routes").info("Timing data enabled - read-along button will be available")
        else:
            template_params.update({"has_timing_data": False})  # No read-along button
            get_logger("routes").info("Standard processing - no read-along functionality")

        return render_template("result.html", **template_params)
    else:
        # Handle errors (common for both routes) with enhanced messaging
        assert result.error is not None, "Error result should have error details"
        enhanced_error_message = get_contextual_error_message(result.error, get_app_config(), original_filename)
        return enhanced_error_message
