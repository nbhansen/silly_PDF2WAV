# routes.py - All Flask route handlers extracted from app.py
# Service context for dependency injection - NO GLOBAL STATE
import contextlib
from dataclasses import dataclass
import json
import os
import time
from typing import Any, Optional, Union

from flask import Response, current_app, jsonify, render_template, request, send_from_directory, url_for
from werkzeug.utils import secure_filename

from domain.models import PageRange, ProcessingResult
from infrastructure.file.file_manager import FileManager
from utils import (
    _get_retry_suggestion,
    _get_user_friendly_error_message,
    allowed_file,
    clean_text_for_display,
    parse_page_range_from_form,
)


@dataclass(frozen=True)
class FileProcessingInfo:
    """Information about processed uploaded file."""

    original_filename: str
    base_filename: str
    pdf_path: str
    page_range: PageRange
    error: Optional[str] = None


@dataclass(frozen=True)
class ProcessingServices:
    """Collection of processing services."""

    service_container: Any
    document_engine: Any
    audio_engine: Any
    text_pipeline: Any


@dataclass(frozen=True)
class ServiceContext:
    """Immutable service context for dependency injection."""

    pdf_service: Optional[object]
    processor_available: bool
    app_config: Optional[object]


def get_service_context() -> ServiceContext:
    """Get service context from Flask app context."""
    return current_app.config["SERVICE_CONTEXT"]  # type: ignore[no-any-return]


def get_pdf_service() -> Any:
    """Get PDF service from context."""
    return get_service_context().pdf_service


def is_processor_available() -> bool:
    """Check if processor is available from context."""
    return get_service_context().processor_available


def get_app_config() -> Any:
    """Get app config from context."""
    return get_service_context().app_config


def register_routes(app: Any) -> None:
    """Register all routes with the Flask app."""

    @app.route("/")  # type: ignore[misc]
    def index() -> str:
        config = get_app_config()
        return render_template("index.html", tts_engine=config.tts_engine.value)

    @app.route("/audio_outputs/<filename>")  # type: ignore[misc]
    def serve_audio(filename: str) -> Response:
        return send_from_directory(app.config["AUDIO_FOLDER"], filename)

    @app.route("/read-along/<filename>")  # type: ignore[misc]
    def read_along_view(filename: str) -> Union[str, tuple[str, int]]:
        """Serve read-along interface for audio file."""
        # Extract base filename (remove extension and _combined suffix)
        base_filename = filename.replace("_combined.mp3", "").replace(".mp3", "").replace(".wav", "")

        # Check if timing data exists
        timing_filename = f"{base_filename}_timing.json"
        timing_path = os.path.join(app.config["AUDIO_FOLDER"], timing_filename)

        if not os.path.exists(timing_path):
            return f"Timing data not found for {filename}. This file was not processed with read-along support.", 404

        # Check if audio file exists
        audio_path = os.path.join(app.config["AUDIO_FOLDER"], filename)
        if not os.path.exists(audio_path):
            return f"Audio file {filename} not found.", 404

        # Load timing data for template rendering
        import json

        try:
            with open(timing_path) as f:
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

    @app.route("/api/timing/<filename>")  # type: ignore[misc]
    def get_timing_data(filename: str) -> Union[Response, tuple[Response, int]]:
        """Serve timing metadata as JSON."""
        timing_filename = f"{filename}_timing.json"
        timing_path = os.path.join(app.config["AUDIO_FOLDER"], timing_filename)

        if not os.path.exists(timing_path):
            return jsonify({"error": "Timing data not found"}), 404

        try:
            with open(timing_path, encoding="utf-8") as f:
                timing_data = json.load(f)

            return jsonify(timing_data)
        except Exception as e:
            print(f"Error serving timing data: {e}")
            return jsonify({"error": "Failed to load timing data"}), 500

    @app.route("/get_pdf_info", methods=["POST"])  # type: ignore[misc]
    def get_pdf_info() -> Union[Response, tuple[Response, int]]:
        service = get_pdf_service()
        if not is_processor_available() or service is None:
            return jsonify({"error": "PDF Service not available"}), 500

        if "pdf_file" not in request.files:
            return jsonify({"error": "No file provided"}), 400

        file = request.files["pdf_file"]
        if not file.filename or file.filename == "" or not allowed_file(file.filename):
            return jsonify({"error": "Invalid file"}), 400

        try:
            # Save temporary file
            original_filename = secure_filename(file.filename)
            temp_path = os.path.join(app.config["UPLOAD_FOLDER"], f"temp_{original_filename}")
            file.save(temp_path)

            # Use document engine to get PDF info
            document_engine = service.get("IDocumentEngine")
            pdf_info = document_engine.get_pdf_info(temp_path)

            # Clean up
            with contextlib.suppress(Exception):
                os.remove(temp_path)

            return jsonify({"total_pages": pdf_info.total_pages, "title": pdf_info.title, "author": pdf_info.author})

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/upload", methods=["POST"])  # type: ignore[misc]
    def upload_file() -> Union[str, tuple[str, int]]:
        """Regular upload WITHOUT timing data."""
        service = get_pdf_service()
        if not is_processor_available() or service is None:
            return "Error: PDF Service is not available."

        if "pdf_file" not in request.files:
            return "No file part in the request."

        file = request.files["pdf_file"]
        if not file.filename or file.filename == "" or not allowed_file(file.filename):
            return "No file selected or invalid file type."

        # Use unified processing logic WITHOUT timing
        result, original_filename, base_filename, error_message = process_upload_request(
            request.form, file, enable_timing=False
        )

        if error_message:
            return error_message

        # Parse page range for display (needed for render function)
        page_range = parse_page_range_from_form(request.form)

        # Render result WITHOUT timing data
        return render_upload_result(result, original_filename, base_filename, page_range, enable_timing=False)

    @app.route("/upload-with-timing", methods=["POST"])  # type: ignore[misc]
    def upload_file_with_timing() -> Union[str, tuple[str, int]]:
        """Upload WITH timing data for read-along functionality."""
        config = get_app_config()
        if config.tts_engine.value == "gemini":
            return "Read-along mode is not available with Gemini TTS. Please use regular upload or switch to Piper TTS."

        service = get_pdf_service()
        if not is_processor_available() or service is None:
            return "Error: PDF Service is not available."

        if "pdf_file" not in request.files:
            return "No file part in the request."

        file = request.files["pdf_file"]
        if not file.filename or file.filename == "" or not allowed_file(file.filename):
            return "No file selected or invalid file type."

        # Use unified processing logic WITH timing
        result, original_filename, base_filename, error_message = process_upload_request(
            request.form, file, enable_timing=True
        )

        if error_message:
            return error_message

        # Parse page range for display (needed for render function)
        page_range = parse_page_range_from_form(request.form)

        # Render result WITH timing data (enables read-along button)
        return render_upload_result(result, original_filename, base_filename, page_range, enable_timing=True)

    @app.route("/admin/file_stats")  # type: ignore[misc]
    def get_file_stats() -> Union[Response, tuple[Response, int]]:
        """Get file management statistics (admin endpoint)."""
        service = get_pdf_service()
        if not is_processor_available() or not service:
            return jsonify({"error": "Service not available"}), 500

        try:
            if hasattr(service, "file_manager") and service.file_manager:
                # Use the FileManager's get_stats method if it exists
                if hasattr(service.file_manager, "get_stats"):
                    stats = service.file_manager.get_stats()
                    return jsonify(stats)
                else:
                    # Fallback: create basic stats manually
                    audio_dir = app.config["AUDIO_FOLDER"]
                    if os.path.exists(audio_dir):
                        files = os.listdir(audio_dir)
                        total_size = sum(
                            os.path.getsize(os.path.join(audio_dir, f))
                            for f in files
                            if os.path.isfile(os.path.join(audio_dir, f))
                        )

                        stats = {
                            "total_files": len(files),
                            "total_size_mb": total_size / (1024 * 1024),
                            "directory": audio_dir,
                            "cleanup_enabled": get_app_config().enable_file_cleanup,
                        }
                        return jsonify(stats)
                    else:
                        return jsonify({"error": "Audio directory not found"}), 404
            else:
                return jsonify({"error": "File management not available"}), 404

        except Exception as e:
            print(f"Admin file_stats error: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route("/admin/cleanup", methods=["POST"])  # type: ignore[misc]
    def manual_cleanup() -> Union[Response, tuple[Response, int]]:
        """Trigger manual file cleanup (admin endpoint)."""
        service = get_pdf_service()
        if not is_processor_available() or not service:
            return jsonify({"error": "Service not available"}), 500

        try:
            max_age_hours = float(request.form.get("max_age_hours", 24.0))

            if hasattr(service, "file_manager") and service.file_manager:
                # Use direct file cleanup if method exists
                if hasattr(service.file_manager, "cleanup_old_files"):
                    result = service.file_manager.cleanup_old_files(max_age_hours)
                    return jsonify(result)
                else:
                    # Fallback: manual cleanup logic
                    audio_dir = app.config["AUDIO_FOLDER"]
                    cutoff_time = time.time() - (max_age_hours * 3600)

                    removed_files = 0
                    bytes_freed = 0
                    errors = []

                    try:
                        for filename in os.listdir(audio_dir):
                            filepath = os.path.join(audio_dir, filename)
                            if os.path.isfile(filepath):
                                file_age = os.path.getmtime(filepath)
                                if file_age < cutoff_time:
                                    try:
                                        file_size = os.path.getsize(filepath)
                                        os.remove(filepath)
                                        removed_files += 1
                                        bytes_freed += file_size
                                        print(f"Cleaned up old file: {filename}")
                                    except Exception as e:
                                        errors.append(f"Failed to remove {filename}: {e!s}")

                        result = {
                            "files_removed": removed_files,
                            "bytes_freed": bytes_freed,
                            "mb_freed": bytes_freed / (1024 * 1024),
                            "errors": errors,
                            "max_age_hours": max_age_hours,
                        }
                        return jsonify(result)

                    except Exception as e:
                        return jsonify({"error": f"Cleanup failed: {e!s}"}), 500
            else:
                return jsonify({"error": "File management not available"}), 404

        except Exception as e:
            print(f"Admin cleanup error: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route("/admin/cleanup_scheduler", methods=["POST"])  # type: ignore[misc]
    def trigger_scheduler_cleanup() -> Union[Response, tuple[Response, int]]:
        """Trigger scheduler's manual cleanup."""
        try:
            service = get_pdf_service()

            # The scheduler should be available through composition root
            if hasattr(service, "cleanup_scheduler") and service.cleanup_scheduler:
                # Trigger manual cleanup if method exists
                if hasattr(service.cleanup_scheduler, "run_manual_cleanup"):
                    result = service.cleanup_scheduler.run_manual_cleanup()
                    return jsonify(result)
                else:
                    return jsonify({"error": "Manual cleanup not supported by scheduler"}), 404
            else:
                return jsonify({"error": "Cleanup scheduler not available"}), 500

        except Exception as e:
            print(f"Scheduler cleanup error: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route("/admin/test")  # type: ignore[misc]
    def test_admin() -> Union[Response, tuple[Response, int]]:
        """Test endpoint to check what's available."""
        try:
            service = get_pdf_service()

            def is_flask_reloader() -> bool:
                return os.environ.get("WERKZEUG_RUN_MAIN") != "true"

            info = {
                "processor_available": is_processor_available(),
                "service_exists": service is not None,
                "has_file_manager_attr": hasattr(service, "file_manager") if service else False,
                "file_manager_exists": (
                    service.file_manager is not None if (service and hasattr(service, "file_manager")) else False
                ),
                "service_type": service.__class__.__name__ if service else "None",
                "file_cleanup_enabled": get_app_config().enable_file_cleanup,
                "is_reloader_process": is_flask_reloader(),
            }

            if service and hasattr(service, "file_manager") and service.file_manager:
                info["file_manager_type"] = service.file_manager.__class__.__name__
                try:
                    if hasattr(service.file_manager, "get_stats"):
                        stats = service.file_manager.get_stats()
                        info["file_stats"] = stats
                except Exception as e:
                    info["file_stats_error"] = str(e)

            return jsonify(info)

        except Exception as e:
            return jsonify({"error": str(e)}), 500


def process_upload_request(
    request_form: Any, uploaded_file: Any, enable_timing: bool = False
) -> tuple[Optional[ProcessingResult], str, str, Optional[str]]:
    """Unified upload processing logic that preserves timing functionality."""
    try:
        # Process and validate uploaded file
        file_info = _process_uploaded_file(uploaded_file, request_form)
        if file_info.error:
            return None, file_info.original_filename, file_info.base_filename, file_info.error

        # Configure processing services
        services = _configure_processing_services()

        # Execute document processing
        processing_result = _execute_document_processing(
            file_info.pdf_path, file_info.base_filename, file_info.page_range, services, enable_timing
        )

        # Clean up uploaded file
        with contextlib.suppress(Exception):
            os.remove(file_info.pdf_path)

        if not processing_result.success or not processing_result.audio_files:
            return processing_result, file_info.original_filename, file_info.base_filename, None

        # Handle timing data and finalize result
        final_result = _handle_timing_data(processing_result, file_info.base_filename, enable_timing, services)

        return final_result, file_info.original_filename, file_info.base_filename, None

    except Exception as e:
        print(f"Upload processing error: {e}")
        import traceback

        traceback.print_exc()
        return None, _get_safe_filename_from_locals(locals()), "", f"An unexpected error occurred: {e!s}"


def _process_uploaded_file(uploaded_file: Any, request_form: Any) -> FileProcessingInfo:
    """Process and validate uploaded file, return file information or error."""
    config = get_app_config()
    original_filename = secure_filename(uploaded_file.filename)
    base_filename_no_ext = os.path.splitext(original_filename)[0]
    pdf_path = os.path.join(config.upload_folder, original_filename)
    uploaded_file.save(pdf_path)

    # Parse and validate page range
    page_range = parse_page_range_from_form(request_form)

    if not page_range.is_full_document():
        services = _configure_processing_services()
        document_engine = services.document_engine
        validation = document_engine.validate_page_range(pdf_path, page_range)
        if not validation.get("valid", False):
            # Clean up file before returning error
            with contextlib.suppress(Exception):
                os.remove(pdf_path)
            return FileProcessingInfo(
                original_filename=original_filename,
                base_filename=base_filename_no_ext,
                pdf_path=pdf_path,
                page_range=page_range,
                error=f"Error: {validation.get('error', 'Invalid page range')}",
            )

    return FileProcessingInfo(
        original_filename=original_filename,
        base_filename=base_filename_no_ext,
        pdf_path=pdf_path,
        page_range=page_range,
    )


def _configure_processing_services() -> ProcessingServices:
    """Configure and return all required processing services."""
    service = get_pdf_service()
    document_engine = service.get("IDocumentEngine")
    audio_engine = service.get("IAudioEngine")
    text_pipeline = service.get("ITextPipeline")

    return ProcessingServices(
        service_container=service,
        document_engine=document_engine,
        audio_engine=audio_engine,
        text_pipeline=text_pipeline,
    )


def _execute_document_processing(
    pdf_path: str, base_filename: str, page_range: PageRange, services: ProcessingServices, enable_timing: bool
) -> ProcessingResult:
    """Execute the core document processing workflow."""
    # Override timing for Gemini TTS
    config = get_app_config()
    enable_timing = enable_timing and config.tts_engine.value != "gemini"

    print(f"Processing {'with timing data' if enable_timing else 'without timing'} for: {base_filename}")

    # Create processing request
    from domain.models import ProcessingRequest

    request_obj = ProcessingRequest(pdf_path=pdf_path, output_name=base_filename, page_range=page_range)

    # Use document engine for complete processing
    result = services.document_engine.process_document(
        request_obj, services.audio_engine, services.text_pipeline, enable_timing
    )
    assert isinstance(result, ProcessingResult)
    return result


def _handle_timing_data(
    processing_result: ProcessingResult, base_filename: str, enable_timing: bool, services: ProcessingServices
) -> ProcessingResult:
    """Handle timing data saving and add debug information to result."""
    timing_data = processing_result.timing_data if processing_result.success else None

    # Save timing data if available and requested
    if enable_timing and timing_data:
        save_timing_data(base_filename, timing_data)

    # Create new result with updated debug info
    from dataclasses import replace

    updated_debug_info = dict(processing_result.debug_info or {})

    # Add timing information to debug info
    if enable_timing and timing_data:
        updated_debug_info.update({"timing_data_created": True, "timing_segments": len(timing_data.text_segments)})
    else:
        updated_debug_info.update({"timing_data_created": False, "timing_segments": 0})

    # Add file management stats to debug info
    try:
        file_manager = services.service_container.get(FileManager)
        if file_manager:
            updated_debug_info["file_management"] = "available"
            updated_debug_info["cleanup_enabled"] = get_app_config().enable_file_cleanup
    except Exception:
        pass  # Don't fail upload if file stats fail

    return replace(processing_result, debug_info=updated_debug_info)


def _get_safe_filename_from_locals(local_vars: dict[str, Any]) -> str:
    """Safely extract filename from local variables for error handling."""
    filename = local_vars.get("original_filename", "unknown")
    return str(filename)  # Ensure we return a string


def render_upload_result(
    result: Optional[ProcessingResult],
    original_filename: str,
    base_filename_no_ext: str,
    page_range: Any,
    enable_timing: bool = False,
) -> str:
    """Render the result template with appropriate parameters."""
    if result is None:
        return render_template("error.html", error_message="Processing failed - no result returned")

    print(f"🔍 DEBUG: result.success={result.success}, result.error={result.error}")
    if result.success:
        display_filename = original_filename
        if not page_range.is_full_document():
            display_filename += f" (pages {page_range.start_page or 1}-{page_range.end_page or 'end'})"

        # CRITICAL: Different template parameters based on timing
        template_params = {
            "audio_files": result.audio_files or [],
            "combined_mp3_file": result.combined_mp3_file,
            "original_filename": display_filename,
            "tts_engine": get_app_config().tts_engine.value,
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
            print("✅ Timing data enabled - read-along button will be available")
        else:
            template_params.update({"has_timing_data": False})  # No read-along button
            print("✅ Standard processing - no read-along functionality")

        return render_template("result.html", **template_params)
    else:
        # Handle errors (common for both routes)
        assert result.error is not None, "Error result should have error details"
        error_message = _get_user_friendly_error_message(result.error)
        retry_suggestion = _get_retry_suggestion(result.error, get_app_config())

        if retry_suggestion:
            return f"Error: {error_message}<br><br>💡 Suggestion: {retry_suggestion}"
        else:
            return f"Error: {error_message}"


def save_timing_data(base_filename: str, timing_metadata: Any) -> None:
    """Save timing metadata as JSON file."""
    # Convert to JSON-serializable format
    timing_json = {
        "total_duration": timing_metadata.total_duration,
        "audio_files": timing_metadata.audio_files,
        "text_segments": [
            {
                "text": clean_text_for_display(segment.text),  # Clean SSML markup
                "start_time": segment.start_time,
                "duration": segment.duration,
                "segment_type": segment.segment_type,
                "chunk_index": segment.chunk_index,
                "sentence_index": segment.sentence_index,
            }
            for segment in timing_metadata.text_segments
        ],
    }

    timing_filename = f"{base_filename}_timing.json"
    timing_path = os.path.join(get_app_config().audio_folder, timing_filename)

    try:
        with open(timing_path, "w", encoding="utf-8") as f:
            json.dump(timing_json, f, indent=2, ensure_ascii=False)

        print(f"Saved timing data: {timing_filename}")

        # Register timing file with file manager if available
        service = get_pdf_service()
        if hasattr(service, "file_manager") and service.file_manager:
            try:
                if hasattr(service.file_manager, "schedule_cleanup"):
                    service.file_manager.schedule_cleanup(timing_filename, 2.0)  # Same cleanup as audio
            except Exception:
                pass

    except Exception as e:
        print(f"Failed to save timing data: {e}")
