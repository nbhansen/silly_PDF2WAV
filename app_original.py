# app.py - Fixed interface issues
from infrastructure.file.cleanup_scheduler import FileCleanupScheduler
from application.composition_root import create_pdf_service_from_env
from domain.errors import ErrorCode, ApplicationError, audio_generation_error
from domain.models import PageRange, ProcessingResult
from application.config.system_config import SystemConfig
import os
import signal
import sys
import atexit
import json
import re
import time
from typing import Optional
from flask import Flask, render_template, request, url_for, send_from_directory, jsonify
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

# Import new configuration system and errors

# Helper function to detect Flask reloader


def is_flask_reloader():
    """Check if we're in Flask debug reloader process"""
    return os.environ.get('WERKZEUG_RUN_MAIN') != 'true'


# Initialize configuration and validate early
try:
    app_config = SystemConfig.from_env()
    print("Configuration loaded successfully!")
except Exception as e:
    print(f"FATAL: Configuration error - {e}")
    print("Please fix your environment variables before starting the application.")
    exit(1)


# Flask App Setup using validated configuration
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = app_config.upload_folder
app.config['AUDIO_FOLDER'] = app_config.audio_folder
app.config['MAX_CONTENT_LENGTH'] = app_config.max_file_size_mb * 1024 * 1024

# Create directories
os.makedirs(app_config.upload_folder, exist_ok=True)
os.makedirs(app_config.audio_folder, exist_ok=True)

# Allowed file extensions
ALLOWED_EXTENSIONS = {'pdf'}

# Global cleanup scheduler
cleanup_scheduler: Optional[FileCleanupScheduler] = None

# Initialize PDF processing service - ONLY in main process
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
    pdf_service = None
    processor_available = False

# Lazy initialization for reloader process


def get_pdf_service():
    """Get PDF service, initializing if needed (for reloader process)"""
    global pdf_service, processor_available

    if pdf_service is None and is_flask_reloader():
        try:
            pdf_service = create_pdf_service_from_env()
            processor_available = True
        except Exception as e:
            print(f"Failed to initialize PDF service in reloader: {e}")
            processor_available = False

    return pdf_service


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def parse_page_range_from_form(form) -> PageRange:
    """Parse page range from Flask form data"""
    use_page_range = form.get('use_page_range') == 'on'

    if not use_page_range:
        return PageRange()

    start_page = None
    end_page = None

    start_page_str = form.get('start_page', '').strip()
    end_page_str = form.get('end_page', '').strip()

    if start_page_str:
        start_page = int(start_page_str)

    if end_page_str:
        end_page = int(end_page_str)

    return PageRange(start_page=start_page, end_page=end_page)


def clean_text_for_display(text: str) -> str:
    """Remove SSML markup and pause markers from text for display"""
    # Remove SSML tags
    text = re.sub(r'<[^>]+>', '', text)

    # Remove pause markers
    text = re.sub(r'\.{3,}', '', text)  # Remove ... sequences
    text = re.sub(r'\(\s*\)', '', text)  # Remove ( ) sequences
    text = re.sub(r'\s+', ' ', text)    # Clean up multiple spaces

    return text.strip()


# Routes
@app.route('/')
def index():
    return render_template('index.html', tts_engine=app_config.tts_engine.value)


@app.route('/audio_outputs/<filename>')
def serve_audio(filename):
    return send_from_directory(app.config['AUDIO_FOLDER'], filename)


@app.route('/read-along/<filename>')
def read_along_view(filename):
    """Serve read-along interface for audio file"""
    # Extract base filename (remove extension and _combined suffix)
    base_filename = filename.replace('_combined.mp3', '').replace('.mp3', '').replace('.wav', '')

    # Check if timing data exists
    timing_filename = f"{base_filename}_timing.json"
    timing_path = os.path.join(app.config['AUDIO_FOLDER'], timing_filename)

    if not os.path.exists(timing_path):
        return f"Timing data not found for {filename}. This file was not processed with read-along support.", 404

    # Check if audio file exists
    audio_path = os.path.join(app.config['AUDIO_FOLDER'], filename)
    if not os.path.exists(audio_path):
        return f"Audio file {filename} not found.", 404

    return render_template('read_along.html',
                           audio_filename=filename,
                           base_filename=base_filename,
                           timing_api_url=url_for('get_timing_data', filename=base_filename))


@app.route('/api/timing/<filename>')
def get_timing_data(filename):
    """Serve timing metadata as JSON"""
    timing_filename = f"{filename}_timing.json"
    timing_path = os.path.join(app.config['AUDIO_FOLDER'], timing_filename)

    if not os.path.exists(timing_path):
        return jsonify({'error': 'Timing data not found'}), 404

    try:
        with open(timing_path, 'r', encoding='utf-8') as f:
            timing_data = json.load(f)

        return jsonify(timing_data)
    except Exception as e:
        print(f"Error serving timing data: {e}")
        return jsonify({'error': 'Failed to load timing data'}), 500


@app.route('/get_pdf_info', methods=['POST'])
def get_pdf_info():
    service = get_pdf_service()
    if not processor_available or service is None:
        return jsonify({'error': 'PDF Service not available'}), 500

    if 'pdf_file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['pdf_file']
    if file.filename == '' or not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file'}), 400

    try:
        # Save temporary file
        original_filename = secure_filename(file.filename)
        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], f"temp_{original_filename}")
        file.save(temp_path)

        # Use OCR provider to get PDF info
        pdf_info = service.ocr_provider.get_pdf_info(temp_path)

        # Clean up
        try:
            os.remove(temp_path)
        except Exception:
            pass

        return jsonify({
            'total_pages': pdf_info.total_pages,
            'title': pdf_info.title,
            'author': pdf_info.author
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


def process_upload_request(request_form, uploaded_file, enable_timing=False):
    """
    Unified upload processing logic that preserves timing functionality.

    Args:
        request_form: Flask request.form
        uploaded_file: Flask uploaded file object
        enable_timing: bool - whether to generate timing data for read-along

    Returns:
        tuple: (result, original_filename, base_filename_no_ext, error_message)
    """
    try:
        # File processing and validation
        original_filename = secure_filename(uploaded_file.filename)
        base_filename_no_ext = os.path.splitext(original_filename)[0]
        pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], original_filename)
        uploaded_file.save(pdf_path)

        # Parse page range
        page_range = parse_page_range_from_form(request_form)

        # Validate page range if specified
        service = get_pdf_service()
        if not page_range.is_full_document():
            validation = service.ocr_provider.validate_range(pdf_path, page_range)
            if not validation.get('valid', False):
                # Clean up file before returning error
                try:
                    os.remove(pdf_path)
                except Exception:
                    pass
                return None, original_filename, base_filename_no_ext, \
                    f"Error: {validation.get('error', 'Invalid page range')}"

        # Convert PageRange to page list for the service
        pages_list = None
        if not page_range.is_full_document():
            start = page_range.start_page or 1
            end = page_range.end_page
            if end is None:
                # Get total pages to determine end
                pdf_info = service.ocr_provider.get_pdf_info(pdf_path)
                end = pdf_info.total_pages
            pages_list = list(range(start - 1, end))  # Convert to 0-based indexing

        # Override timing for Gemini TTS
        enable_timing = enable_timing and app_config.tts_engine.value != 'gemini'
        
        # CRITICAL: Process using the correct service method
        print(f"Processing {'with timing data' if enable_timing else 'without timing'} for: {original_filename}")

        # Use the existing method that returns TimedAudioResult
        timed_result = service.process_pdf_and_generate_audio(
            filepath=pdf_path,
            output_name=base_filename_no_ext,
            pages=pages_list
        )

        # Clean up uploaded file
        try:
            os.remove(pdf_path)
        except Exception:
            pass

        if not timed_result or not timed_result.audio_files:
            return ProcessingResult.failure_result(
                audio_generation_error("No audio files were generated")
            ), original_filename, base_filename_no_ext, None

        # Save timing data if available and requested
        if enable_timing and timed_result.timing_data:
            save_timing_data(base_filename_no_ext, timed_result.timing_data)

        # Convert TimedAudioResult to ProcessingResult
        result = ProcessingResult.success_result(
            audio_files=[os.path.basename(f) for f in timed_result.audio_files],
            combined_mp3=os.path.basename(timed_result.combined_mp3) if timed_result.combined_mp3 else None,
            debug_info={
                "audio_files_count": len(timed_result.audio_files),
                "combined_mp3_created": timed_result.combined_mp3 is not None,
                "timing_data_created": enable_timing and timed_result.timing_data is not None,
                "timing_segments": len(timed_result.timing_data.text_segments)
                if (enable_timing and timed_result.timing_data) else 0
            }
        )

        # Add file management stats to debug info
        if hasattr(service, 'file_manager') and service.file_manager:
            try:
                if hasattr(service.file_manager, 'get_file_info'):
                    result.debug_info['file_management'] = 'available'
                result.debug_info['cleanup_enabled'] = app_config.enable_file_cleanup
            except Exception:
                pass  # Don't fail upload if file stats fail

        return result, original_filename, base_filename_no_ext, None

    except Exception as e:
        print(f"Upload processing error: {e}")
        import traceback
        traceback.print_exc()
        return None, original_filename if 'original_filename' in locals() else 'unknown', '', \
            f"An unexpected error occurred: {str(e)}"


def render_upload_result(result, original_filename, base_filename_no_ext, page_range, enable_timing=False):
    """
    Render the result template with appropriate parameters.

    Args:
        result: ProcessingResult object
        original_filename: Original PDF filename
        base_filename_no_ext: Base filename without extension
        page_range: PageRange object
        enable_timing: bool - whether timing data was generated

    Returns:
        Rendered template response
    """
    if result.success:
        display_filename = original_filename
        if not page_range.is_full_document():
            display_filename += f" (pages {page_range.start_page or 1}-{page_range.end_page or 'end'})"

        # CRITICAL: Different template parameters based on timing
        template_params = {
            'audio_files': result.audio_files or [],
            'combined_mp3_file': result.combined_mp3_file,
            'original_filename': display_filename,
            'tts_engine': app_config.tts_engine.value,
            'file_count': len(result.audio_files) if result.audio_files else 0,
            'debug_info': result.debug_info
        }

        # Add timing-specific parameters for read-along functionality
        if enable_timing:
            template_params.update({
                'has_timing_data': True,      # Enables read-along button
                'base_filename': base_filename_no_ext  # For read-along URL
            })
            print("✅ Timing data enabled - read-along button will be available")
        else:
            template_params.update({
                'has_timing_data': False     # No read-along button
            })
            print("✅ Standard processing - no read-along functionality")

        return render_template('result.html', **template_params)
    else:
        # Handle errors (common for both routes)
        error_message = _get_user_friendly_error_message(result.error)
        retry_suggestion = _get_retry_suggestion(result.error)

        if retry_suggestion:
            return f"Error: {error_message}<br><br>💡 Suggestion: {retry_suggestion}"
        else:
            return f"Error: {error_message}"


# Upload routes - THE CORRECT ROUTES!
@app.route('/upload', methods=['POST'])
def upload_file():
    """Regular upload WITHOUT timing data"""
    service = get_pdf_service()
    if not processor_available or service is None:
        return "Error: PDF Service is not available."

    if 'pdf_file' not in request.files:
        return "No file part in the request."

    file = request.files['pdf_file']
    if file.filename == '' or not allowed_file(file.filename):
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


@app.route('/upload-with-timing', methods=['POST'])
def upload_file_with_timing():
    """Upload WITH timing data for read-along functionality"""
    if app_config.tts_engine.value == 'gemini':
        return "Read-along mode is not available with Gemini TTS. Please use regular upload or switch to Piper TTS."
    
    service = get_pdf_service()
    if not processor_available or service is None:
        return "Error: PDF Service is not available."

    if 'pdf_file' not in request.files:
        return "No file part in the request."

    file = request.files['pdf_file']
    if file.filename == '' or not allowed_file(file.filename):
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


def save_timing_data(base_filename, timing_metadata):
    """Save timing metadata as JSON file"""
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
                "sentence_index": segment.sentence_index
            }
            for segment in timing_metadata.text_segments
        ]
    }

    timing_filename = f"{base_filename}_timing.json"
    timing_path = os.path.join(app.config['AUDIO_FOLDER'], timing_filename)

    try:
        with open(timing_path, 'w', encoding='utf-8') as f:
            json.dump(timing_json, f, indent=2, ensure_ascii=False)

        print(f"Saved timing data: {timing_filename}")

        # Register timing file with file manager if available
        service = get_pdf_service()
        if hasattr(service, 'file_manager') and service.file_manager:
            try:
                if hasattr(service.file_manager, 'schedule_cleanup'):
                    service.file_manager.schedule_cleanup(timing_filename, 2.0)  # Same cleanup as audio
            except Exception:
                pass

    except Exception as e:
        print(f"Failed to save timing data: {e}")


# Fixed admin endpoints
@app.route('/admin/file_stats')
def get_file_stats():
    """Get file management statistics (admin endpoint)"""
    service = get_pdf_service()
    if not processor_available or not service:
        return jsonify({'error': 'Service not available'}), 500

    try:
        if hasattr(service, 'file_manager') and service.file_manager:
            # Use the FileManager's get_stats method if it exists
            if hasattr(service.file_manager, 'get_stats'):
                stats = service.file_manager.get_stats()
                return jsonify(stats)
            else:
                # Fallback: create basic stats manually
                audio_dir = app.config['AUDIO_FOLDER']
                if os.path.exists(audio_dir):
                    files = os.listdir(audio_dir)
                    total_size = sum(os.path.getsize(os.path.join(audio_dir, f))
                                     for f in files if os.path.isfile(os.path.join(audio_dir, f)))

                    stats = {
                        'total_files': len(files),
                        'total_size_mb': total_size / (1024 * 1024),
                        'directory': audio_dir,
                        'cleanup_enabled': app_config.enable_file_cleanup
                    }
                    return jsonify(stats)
                else:
                    return jsonify({'error': 'Audio directory not found'}), 404
        else:
            return jsonify({'error': 'File management not available'}), 404

    except Exception as e:
        print(f"Admin file_stats error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/admin/cleanup', methods=['POST'])
def manual_cleanup():
    """Trigger manual file cleanup (admin endpoint)"""
    service = get_pdf_service()
    if not processor_available or not service:
        return jsonify({'error': 'Service not available'}), 500

    try:
        max_age_hours = float(request.form.get('max_age_hours', 24.0))

        if hasattr(service, 'file_manager') and service.file_manager:
            # Use direct file cleanup if method exists
            if hasattr(service.file_manager, 'cleanup_old_files'):
                result = service.file_manager.cleanup_old_files(max_age_hours)
                return jsonify(result)
            else:
                # Fallback: manual cleanup logic
                audio_dir = app.config['AUDIO_FOLDER']
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
                                    errors.append(f"Failed to remove {filename}: {str(e)}")

                    result = {
                        'files_removed': removed_files,
                        'bytes_freed': bytes_freed,
                        'mb_freed': bytes_freed / (1024 * 1024),
                        'errors': errors,
                        'max_age_hours': max_age_hours
                    }
                    return jsonify(result)

                except Exception as e:
                    return jsonify({'error': f'Cleanup failed: {str(e)}'}), 500
        else:
            return jsonify({'error': 'File management not available'}), 404

    except Exception as e:
        print(f"Admin cleanup error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/admin/cleanup_scheduler', methods=['POST'])
def trigger_scheduler_cleanup():
    """Trigger scheduler's manual cleanup"""
    try:
        service = get_pdf_service()

        # The scheduler should be available through composition root
        if hasattr(service, 'cleanup_scheduler') and service.cleanup_scheduler:
            # Trigger manual cleanup if method exists
            if hasattr(service.cleanup_scheduler, 'run_manual_cleanup'):
                result = service.cleanup_scheduler.run_manual_cleanup()
                return jsonify(result)
            else:
                return jsonify({'error': 'Manual cleanup not supported by scheduler'}), 404
        else:
            return jsonify({'error': 'Cleanup scheduler not available'}), 500

    except Exception as e:
        print(f"Scheduler cleanup error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/admin/test')
def test_admin():
    """Test endpoint to check what's available"""
    try:
        service = get_pdf_service()
        info = {
            'processor_available': processor_available,
            'service_exists': service is not None,
            'has_file_manager_attr': hasattr(service, 'file_manager') if service else False,
            'file_manager_exists': service.file_manager is not None if (service and hasattr(service, 'file_manager')) else False,
            'service_type': service.__class__.__name__ if service else 'None',
            'cleanup_scheduler_exists': cleanup_scheduler is not None,
            'file_cleanup_enabled': app_config.enable_file_cleanup,
            'is_reloader_process': is_flask_reloader()
        }

        if service and hasattr(service, 'file_manager') and service.file_manager:
            info['file_manager_type'] = service.file_manager.__class__.__name__
            try:
                if hasattr(service.file_manager, 'get_stats'):
                    stats = service.file_manager.get_stats()
                    info['file_stats'] = stats
            except Exception as e:
                info['file_stats_error'] = str(e)

        return jsonify(info)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


def _get_user_friendly_error_message(error: 'ApplicationError') -> str:
    """Convert technical error to user-friendly message"""
    if error.code == ErrorCode.FILE_NOT_FOUND:
        return "The uploaded file could not be found or accessed."
    elif error.code == ErrorCode.TEXT_EXTRACTION_FAILED:
        return "Could not extract text from the PDF. The file might be corrupted, image-only, or password-protected."
    elif error.code == ErrorCode.TEXT_CLEANING_FAILED:
        return "Failed to process the extracted text for audio conversion."
    elif error.code == ErrorCode.AUDIO_GENERATION_FAILED:
        return "Failed to generate audio from the text. This might be a temporary issue with the text-to-speech service."
    elif error.code == ErrorCode.TTS_ENGINE_ERROR:
        return "Text-to-speech service encountered an error. This might be temporary."
    elif error.code == ErrorCode.LLM_PROVIDER_ERROR:
        return "Text cleaning service encountered an error. This might be temporary."
    elif error.code == ErrorCode.INVALID_PAGE_RANGE:
        return f"Invalid page range: {error.details}"
    elif error.code == ErrorCode.FILE_SIZE_ERROR:
        return str(error.message)
    elif error.code == ErrorCode.UNSUPPORTED_FILE_TYPE:
        return "Only PDF files are supported for conversion."
    else:
        return error.message


def _get_retry_suggestion(error: 'ApplicationError') -> str:
    """Get retry suggestion based on error type"""
    if error.retryable:
        if error.code in [ErrorCode.TTS_ENGINE_ERROR, ErrorCode.AUDIO_GENERATION_FAILED]:
            return "Please try again in a few moments. If the problem persists, the text-to-speech service might be temporarily unavailable."
        elif error.code == ErrorCode.LLM_PROVIDER_ERROR:
            return "Please try again in a few moments, or disable text cleaning in your configuration."
        elif error.code == ErrorCode.TEXT_CLEANING_FAILED:
            return "Try again or consider disabling text cleaning (set ENABLE_TEXT_CLEANING=False) if the problem persists."
        else:
            return "This error might be temporary. Please try again."
    else:
        if error.code == ErrorCode.TEXT_EXTRACTION_FAILED:
            return "Try a different PDF file, or ensure the PDF is not password-protected or image-only."
        elif error.code == ErrorCode.FILE_SIZE_ERROR:
            return f"Please use a smaller PDF file (maximum {app_config.max_file_size_mb}MB)."
        elif error.code == ErrorCode.INVALID_PAGE_RANGE:
            return "Please check the page numbers and try again."

    return ""

# Graceful shutdown handlers


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


# Register shutdown handlers
atexit.register(lambda: shutdown_cleanup() if not is_flask_reloader() else None)
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


@app.errorhandler(413)
def too_large(e):
    return f"File is too large. Maximum file size is {app_config.max_file_size_mb}MB.", 413


@app.errorhandler(Exception)
def handle_exception(e):
    import traceback
    print(f"🚨 FULL ERROR TRACEBACK:")
    print(traceback.format_exc())  # This will show the full error
    print(f"🚨 Exception type: {type(e)}")
    print(f"🚨 Exception message: {str(e)}")
    return f"An error occurred: {str(e)}", 500


# Debug: Print all registered routes
print("🔧 REGISTERED ROUTES:")
for rule in app.url_map.iter_rules():
    print(f"  {rule.rule} -> {rule.endpoint}")
print("🔧 END ROUTES")

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
