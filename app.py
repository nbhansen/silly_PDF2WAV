# app.py - Updated to use SystemConfig with File Management and Read-Along Support
import os
import signal
import sys
import atexit
import json
import re
from typing import Optional
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, jsonify
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

# Import new configuration system and errors
from application.config.system_config import SystemConfig
from domain.models import ProcessingRequest, PageRange, ProcessingResult
from domain.errors import ErrorCode, ApplicationError, invalid_page_range_error, file_size_error, unsupported_file_type_error, text_extraction_error, text_cleaning_error, audio_generation_error
from application.composition_root import create_pdf_service_from_env
from infrastructure.file.cleanup_scheduler import FileCleanupScheduler

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

# Initialize PDF processing service
print("Initializing PDF Processing Service...")
try:
    pdf_service = create_pdf_service_from_env()
    print("PDF Processing Service initialized successfully")
    processor_available = True
    
    # Initialize and start file cleanup scheduler
    if hasattr(pdf_service, 'file_manager') and pdf_service.file_manager:
        cleanup_scheduler = FileCleanupScheduler(pdf_service.file_manager, app_config)
        cleanup_scheduler.start()
        print("File cleanup scheduler started")
    else:
        print("File management not available - cleanup scheduler not started")
    
except Exception as e:
    print(f"CRITICAL: PDF Service initialization failed: {e}")
    pdf_service = None
    processor_available = False

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
    return render_template('index.html')

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
    if not processor_available or pdf_service is None:
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
        
        # Use service
        pdf_info = pdf_service.get_pdf_info(temp_path)
        
        # Clean up
        try:
            os.remove(temp_path)
        except:
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
    if not processor_available or pdf_service is None:
        return "Error: PDF Service is not available."

    if 'pdf_file' not in request.files:
        return "No file part in the request."
    
    file = request.files['pdf_file']
    if file.filename == '' or not allowed_file(file.filename):
        return "No file selected or invalid file type."
    
    try:
        # Process upload
        original_filename = secure_filename(file.filename)
        base_filename_no_ext = os.path.splitext(original_filename)[0]
        pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], original_filename)
        file.save(pdf_path)
        
        # Parse page range
        page_range = parse_page_range_from_form(request.form)
        
        # Validate page range if specified
        if not page_range.is_full_document():
            validation = pdf_service.validate_page_range(pdf_path, page_range)
            if not validation.get('valid', False):
                # Clean up file before returning error
                try:
                    os.remove(pdf_path)
                except:
                    pass
                return f"Error: {validation.get('error', 'Invalid page range')}"
        
        # Create processing request
        request_model = ProcessingRequest(
            pdf_path=pdf_path,
            output_name=base_filename_no_ext,
            page_range=page_range
        )
        
        # Use service with structured error handling
        result = pdf_service.process_pdf(request_model)
        
        # Clean up uploaded file
        try:
            os.remove(pdf_path)
        except:
            pass
        
        # Add file management stats to debug info
        if result.success and result.debug_info:
            if hasattr(pdf_service, 'file_manager') and pdf_service.file_manager:
                try:
                    file_stats = pdf_service.file_manager.get_stats()
                    result.debug_info['file_stats'] = {
                        'total_files': file_stats['total_files'],
                        'total_size_mb': file_stats['total_size_mb'],
                        'cleanup_enabled': app_config.enable_file_cleanup
                    }
                except:
                    pass  # Don't fail upload if file stats fail
        
        # Handle result with structured errors
        if result.success:
            display_filename = original_filename
            if not page_range.is_full_document():
                display_filename += f" (pages {page_range.start_page or 1}-{page_range.end_page or 'end'})"
            
            return render_template('result.html', 
                                 audio_files=result.audio_files or [],           
                                 combined_mp3_file=result.combined_mp3_file,
                                 original_filename=display_filename,
                                 tts_engine=app_config.tts_engine.value,
                                 file_count=len(result.audio_files) if result.audio_files else 0,
                                 debug_info=result.debug_info)
        else:
            # Handle structured errors with appropriate user messages
            error_message = _get_user_friendly_error_message(result.error)
            retry_suggestion = _get_retry_suggestion(result.error)
            
            if retry_suggestion:
                return f"Error: {error_message}<br><br>💡 Suggestion: {retry_suggestion}"
            else:
                return f"Error: {error_message}"
            
    except Exception as e:
        print(f"Upload processing error: {e}")
        return f"An unexpected error occurred: {str(e)}"

@app.route('/upload-with-timing', methods=['POST'])
def upload_file_with_timing():
    """Upload and process PDF with timing data generation"""
    if not processor_available or pdf_service is None:
        return "Error: PDF Service is not available."

    if 'pdf_file' not in request.files:
        return "No file part in the request."
    
    file = request.files['pdf_file']
    if file.filename == '' or not allowed_file(file.filename):
        return "No file selected or invalid file type."
    
    try:
        # Process upload (same as regular upload)
        original_filename = secure_filename(file.filename)
        base_filename_no_ext = os.path.splitext(original_filename)[0]
        pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], original_filename)
        file.save(pdf_path)
        
        # Parse page range
        page_range = parse_page_range_from_form(request.form)
        
        # Validate page range if specified
        if not page_range.is_full_document():
            validation = pdf_service.validate_page_range(pdf_path, page_range)
            if not validation.get('valid', False):
                try:
                    os.remove(pdf_path)
                except:
                    pass
                return f"Error: {validation.get('error', 'Invalid page range')}"
        
        # Create processing request
        request_model = ProcessingRequest(
            pdf_path=pdf_path,
            output_name=base_filename_no_ext,
            page_range=page_range
        )
        
        # Use timing-enabled processing
        result = process_pdf_with_timing(request_model)
        
        # Clean up uploaded file
        try:
            os.remove(pdf_path)
        except:
            pass
        
        if result.success:
            display_filename = original_filename
            if not page_range.is_full_document():
                display_filename += f" (pages {page_range.start_page or 1}-{page_range.end_page or 'end'})"
            
            return render_template('result.html', 
                                 audio_files=result.audio_files or [],           
                                 combined_mp3_file=result.combined_mp3_file,
                                 original_filename=display_filename,
                                 tts_engine=app_config.tts_engine.value,
                                 file_count=len(result.audio_files) if result.audio_files else 0,
                                 debug_info=result.debug_info,
                                 has_timing_data=True,  # Flag for read-along button
                                 base_filename=base_filename_no_ext)
        else:
            error_message = _get_user_friendly_error_message(result.error)
            retry_suggestion = _get_retry_suggestion(result.error)
            
            if retry_suggestion:
                return f"Error: {error_message}<br><br>💡 Suggestion: {retry_suggestion}"
            else:
                return f"Error: {error_message}"
            
    except Exception as e:
        print(f"Upload with timing processing error: {e}")
        return f"An unexpected error occurred: {str(e)}"

def process_pdf_with_timing(request_model):
    """Process PDF using timing-enabled service"""
    try:
        # Extract text
        raw_text = pdf_service.text_extractor.extract_text(request_model.pdf_path, request_model.page_range)
        if not raw_text or raw_text.startswith("Error"):
            return ProcessingResult.failure_result(text_extraction_error(raw_text))
        
        # Clean text
        clean_text_chunks = pdf_service.text_cleaner.clean_text(raw_text, pdf_service.llm_provider)
        if not clean_text_chunks:
            return ProcessingResult.failure_result(text_cleaning_error("No valid text chunks produced"))
        
        # Generate audio with timing
        timed_result = pdf_service.audio_generator.generate_audio_with_timing(
            clean_text_chunks,
            request_model.output_name,
            app.config['AUDIO_FOLDER'],
            pdf_service.tts_engine
        )
        
        if not timed_result.audio_files:
            return ProcessingResult.failure_result(audio_generation_error("No audio files were generated"))
        
        # Save timing data as JSON file
        if timed_result.timing_data:
            save_timing_data(request_model.output_name, timed_result.timing_data)
        
        # Build debug info
        debug_info = {
            "raw_text_length": len(raw_text),
            "text_chunks_count": len(clean_text_chunks),
            "audio_files_count": len(timed_result.audio_files),
            "combined_mp3_created": timed_result.combined_mp3 is not None,
            "timing_data_created": timed_result.timing_data is not None,
            "timing_segments": len(timed_result.timing_data.text_segments) if timed_result.timing_data else 0
        }
        
        return ProcessingResult.success_result(
            audio_files=timed_result.audio_files,
            combined_mp3=timed_result.combined_mp3,
            debug_info=debug_info
        )
        
    except Exception as e:
        print(f"Timing processing error: {e}")
        return ProcessingResult.failure_result(ApplicationError(
            code=ErrorCode.UNKNOWN_ERROR,
            message=f"Processing with timing failed: {str(e)}",
            details=e.__class__.__name__,
            retryable=False
        ))

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
        if hasattr(pdf_service, 'file_manager') and pdf_service.file_manager:
            try:
                pdf_service.file_manager.schedule_cleanup(timing_filename, 2.0)  # Same cleanup as audio
            except:
                pass
                
    except Exception as e:
        print(f"Failed to save timing data: {e}")

# Admin endpoints for file management
@app.route('/admin/file_stats')
def get_file_stats():
    """Get file management statistics (admin endpoint)"""
    if not processor_available or not pdf_service:
        return jsonify({'error': 'Service not available'}), 500
    
    try:
        if hasattr(pdf_service, 'get_file_management_stats'):
            stats = pdf_service.get_file_management_stats()
            if stats:
                return jsonify(stats)
            else:
                return jsonify({'error': 'File management not enabled'}), 404
        else:
            return jsonify({'error': 'File management not implemented'}), 404
    except Exception as e:
        print(f"Admin file_stats error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/admin/cleanup', methods=['POST'])
def manual_cleanup():
    """Trigger manual file cleanup (admin endpoint)"""
    if not processor_available or not pdf_service:
        return jsonify({'error': 'Service not available'}), 500
    
    try:
        # Get max_age from request or use default
        max_age_hours = float(request.form.get('max_age_hours', 24.0))
        
        if hasattr(pdf_service, 'cleanup_old_files'):
            result = pdf_service.cleanup_old_files(max_age_hours)
            if result:
                return jsonify(result)
            else:
                return jsonify({'error': 'File management not enabled'}), 404
        else:
            return jsonify({'error': 'Cleanup not implemented'}), 404
    except Exception as e:
        print(f"Admin cleanup error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/admin/cleanup_scheduler', methods=['POST'])
def trigger_scheduler_cleanup():
    """Trigger scheduler's manual cleanup"""
    if not cleanup_scheduler:
        return jsonify({'error': 'Cleanup scheduler not available'}), 500
    
    try:
        result = cleanup_scheduler.run_manual_cleanup()
        return jsonify(result)
    except Exception as e:
        print(f"Scheduler cleanup error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/admin/test')
def test_admin():
    """Test endpoint to check what's available"""
    try:
        info = {
            'processor_available': processor_available,
            'pdf_service_exists': pdf_service is not None,
            'has_file_manager_attr': hasattr(pdf_service, 'file_manager') if pdf_service else False,
            'file_manager_exists': pdf_service.file_manager is not None if (pdf_service and hasattr(pdf_service, 'file_manager')) else False,
            'pdf_service_type': pdf_service.__class__.__name__ if pdf_service else 'None',
            'cleanup_scheduler_exists': cleanup_scheduler is not None,
            'file_cleanup_enabled': app_config.enable_file_cleanup
        }
        
        if pdf_service and hasattr(pdf_service, 'file_manager') and pdf_service.file_manager:
            info['file_manager_type'] = pdf_service.file_manager.__class__.__name__
            try:
                stats = pdf_service.file_manager.get_stats()
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
    shutdown_cleanup()
    sys.exit(0)

# Register shutdown handlers
atexit.register(shutdown_cleanup)
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

@app.errorhandler(413)
def too_large(e):
    return f"File is too large. Maximum file size is {app_config.max_file_size_mb}MB.", 413

@app.errorhandler(Exception)
def handle_exception(e):
    print(f"Unhandled exception: {e}")
    return f"An error occurred: {str(e)}", 500

if __name__ == '__main__':
    print("Starting Flask development server...")
    print(f"TTS Engine: {app_config.tts_engine.value}")
    print(f"Text Cleaning: {'Enabled' if app_config.enable_text_cleaning else 'Disabled'}")
    print(f"File Cleanup: {'Enabled' if app_config.enable_file_cleanup else 'Disabled'}")
    
    try:
        app.run(debug=True, host='0.0.0.0', port=5000)
    finally:
        shutdown_cleanup()