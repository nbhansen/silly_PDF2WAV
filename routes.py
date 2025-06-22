# routes.py - All Flask route handlers extracted from app.py
import os
import json
import time
from typing import Optional
from flask import render_template, request, url_for, send_from_directory, jsonify, current_app as app
from werkzeug.utils import secure_filename

from domain.errors import audio_generation_error
from domain.models import ProcessingResult, TimedAudioResult
from infrastructure.file.file_manager import FileManager
from application.config.system_config import SystemConfig
from utils import (
    allowed_file, parse_page_range_from_form, clean_text_for_display,
    _get_user_friendly_error_message, _get_retry_suggestion
)


# Global variables for services (will be set by app.py)
pdf_service = None
processor_available = False
app_config = SystemConfig.from_env()


def get_pdf_service():
    """Get PDF service"""
    return pdf_service


def is_processor_available():
    """Check if processor is available"""
    return processor_available


def set_services(service, available):
    """Set the services from app.py to avoid circular import"""
    global pdf_service, processor_available
    pdf_service = service
    processor_available = available


def register_routes(app):
    """Register all routes with the Flask app"""
    
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
        if not is_processor_available() or service is None:
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

            # Use document engine to get PDF info
            document_engine = service.get('IDocumentEngine')
            pdf_info = document_engine.get_pdf_info(temp_path)

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

    @app.route('/upload', methods=['POST'])
    def upload_file():
        """Regular upload WITHOUT timing data"""
        service = get_pdf_service()
        if not is_processor_available() or service is None:
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
        if not is_processor_available() or service is None:
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
            
            def is_flask_reloader():
                return os.environ.get('WERKZEUG_RUN_MAIN') != 'true'
            
            info = {
                'processor_available': processor_available,
                'service_exists': service is not None,
                'has_file_manager_attr': hasattr(service, 'file_manager') if service else False,
                'file_manager_exists': service.file_manager is not None if (service and hasattr(service, 'file_manager')) else False,
                'service_type': service.__class__.__name__ if service else 'None',
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


def process_upload_request(request_form, uploaded_file, enable_timing=False):
    """
    Unified upload processing logic that preserves timing functionality.
    """
    try:
        # File processing and validation
        original_filename = secure_filename(uploaded_file.filename)
        base_filename_no_ext = os.path.splitext(original_filename)[0]
        pdf_path = os.path.join(app_config.upload_folder, original_filename)
        uploaded_file.save(pdf_path)

        # Parse page range
        page_range = parse_page_range_from_form(request_form)

        # Get new architecture services
        service = get_pdf_service()
        document_engine = service.get('IDocumentEngine')
        audio_engine = service.get('IAudioEngine')
        text_pipeline = service.get('ITextPipeline')
        
        # Validate page range if specified
        if not page_range.is_full_document():
            validation = document_engine.validate_page_range(pdf_path, page_range)
            if not validation.get('valid', False):
                # Clean up file before returning error
                try:
                    os.remove(pdf_path)
                except Exception:
                    pass
                return None, original_filename, base_filename_no_ext, \
                    f"Error: {validation.get('error', 'Invalid page range')}"

        # Override timing for Gemini TTS
        enable_timing = enable_timing and app_config.tts_engine.value != 'gemini'
        
        # CRITICAL: Process using new consolidated architecture
        print(f"Processing {'with timing data' if enable_timing else 'without timing'} for: {original_filename}")

        # Create processing request
        from domain.models import ProcessingRequest
        request_obj = ProcessingRequest(
            pdf_path=pdf_path,
            output_name=base_filename_no_ext,
            page_range=page_range
        )
        
        # Use new document engine for complete processing
        processing_result = document_engine.process_document(request_obj, audio_engine, text_pipeline, enable_timing)
        
        # Convert ProcessingResult to TimedAudioResult for compatibility
        if processing_result.success:
            timed_result = TimedAudioResult(
                audio_files=[os.path.join(app.config['AUDIO_FOLDER'], f) for f in processing_result.audio_files],
                combined_mp3=os.path.join(app.config['AUDIO_FOLDER'], processing_result.combined_mp3) if processing_result.combined_mp3 else None,
                timing_data=None  # Timing data would be generated separately if needed
            )
        else:
            timed_result = None

        # Clean up uploaded file
        try:
            os.remove(pdf_path)
        except Exception:
            pass

        if not processing_result.success or not processing_result.audio_files:
            return processing_result, original_filename, base_filename_no_ext, None

        # Save timing data if available and requested
        if enable_timing and timed_result.timing_data:
            save_timing_data(base_filename_no_ext, timed_result.timing_data)

        # Use the ProcessingResult directly from new architecture
        result = processing_result
        
        # Add timing information to debug info if available
        if enable_timing and timed_result and timed_result.timing_data:
            result.debug_info.update({
                "timing_data_created": True,
                "timing_segments": len(timed_result.timing_data.text_segments)
            })
        else:
            result.debug_info.update({
                "timing_data_created": False,
                "timing_segments": 0
            })

        # Add file management stats to debug info
        try:
            file_manager = service.get(FileManager)
            if file_manager:
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
    timing_path = os.path.join(app_config.audio_folder, timing_filename)

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