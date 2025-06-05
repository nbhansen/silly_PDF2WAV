# app.py - Clean Architecture Version
import os
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, jsonify
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import new clean architecture
from domain.models import ProcessingRequest, PageRange
from application.composition_root import create_pdf_service_from_env

# Configuration
UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'uploads')
AUDIO_FOLDER = os.getenv('AUDIO_FOLDER', 'audio_outputs')
ALLOWED_EXTENSIONS = set(os.getenv('ALLOWED_EXTENSIONS', 'pdf').split(','))

# Flask App Setup
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['AUDIO_FOLDER'] = AUDIO_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(AUDIO_FOLDER, exist_ok=True)

# Initialize service using clean architecture
print("Initializing PDF Processing Service...")
try:
    pdf_service = create_pdf_service_from_env()
    print("PDF Processing Service initialized successfully")
    processor_available = True
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

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/audio_outputs/<filename>')
def serve_audio(filename):
    return send_from_directory(app.config['AUDIO_FOLDER'], filename)

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
                return f"Error: {validation.get('error', 'Invalid page range')}"
        
        # Create processing request (domain model)
        request_model = ProcessingRequest(
            pdf_path=pdf_path,
            output_name=base_filename_no_ext,
            page_range=page_range
        )
        
        # Use service (pure business logic)
        result = pdf_service.process_pdf(request_model)
        
        # Clean up
        try:
            os.remove(pdf_path)
        except:
            pass
        
        # Handle result
        if result.success:
            display_filename = original_filename
            if not page_range.is_full_document():
                display_filename += f" (pages {page_range.start_page or 1}-{page_range.end_page or 'end'})"
            
            return render_template('result.html', 
                                 audio_files=result.audio_files or [],           
                                 combined_mp3_file=result.combined_mp3_file,
                                 original_filename=display_filename,
                                 tts_engine=os.getenv('TTS_ENGINE', 'coqui'),
                                 file_count=len(result.audio_files) if result.audio_files else 0,
                                 debug_info=result.debug_info)
        else:
            return f"Error: {result.error}"
            
    except Exception as e:
        print(f"Upload processing error: {e}")
        return f"An error occurred: {str(e)}"

@app.errorhandler(413)
def too_large(e):
    return "File is too large. Maximum file size is 100MB.", 413

@app.errorhandler(Exception)
def handle_exception(e):
    print(f"Unhandled exception: {e}")
    return f"An error occurred: {str(e)}", 500

if __name__ == '__main__':
    print("Starting Flask development server...")
    print(f"TTS Engine: {os.getenv('TTS_ENGINE', 'coqui')}")
    app.run(debug=True, host='0.0.0.0', port=5000)