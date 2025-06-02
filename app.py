# app.py - Updated with page range support
import os
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, jsonify
from werkzeug.utils import secure_filename

# Import the processor architecture
from processors import PDFProcessor

# --- Configuration ---
UPLOAD_FOLDER = 'uploads'
AUDIO_FOLDER = 'audio_outputs'
ALLOWED_EXTENSIONS = {'pdf'}

# !! IMPORTANT !! Replace with your actual API key
GOOGLE_AI_API_KEY = "notmyrealkey"  # Your key

# --- TTS Engine Configuration ---
_SELECTED_TTS_ENGINE_CONFIG = "coqui"  # or "gtts", "bark"
TTS_ENGINE_KWARGS = {}

if _SELECTED_TTS_ENGINE_CONFIG.lower() == "coqui":
    TTS_ENGINE_KWARGS = {
        "model_name": "tts_models/en/ljspeech/vits", 
        "use_gpu_if_available": True,
    }
    SELECTED_TTS_ENGINE = "Coqui TTS"
elif _SELECTED_TTS_ENGINE_CONFIG.lower() == "gtts":
    TTS_ENGINE_KWARGS = {
        "lang": "en",
        "tld": "co.uk"
    }
    SELECTED_TTS_ENGINE = "gTTS"
elif _SELECTED_TTS_ENGINE_CONFIG.lower() == "bark": 
    TTS_ENGINE_KWARGS = {
        "use_gpu_if_available": True,
        "use_small_models": True, 
        "history_prompt": None    
    }
    SELECTED_TTS_ENGINE = "Bark"
else:
    SELECTED_TTS_ENGINE = _SELECTED_TTS_ENGINE_CONFIG.upper()

# --- Flask App Setup ---
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['AUDIO_FOLDER'] = AUDIO_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max file size

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(AUDIO_FOLDER, exist_ok=True)

# Initialize the PDFProcessor
print("Initializing PDFProcessor...")
try:
    pdf_processor = PDFProcessor(
        google_api_key=GOOGLE_AI_API_KEY,
        tts_engine=_SELECTED_TTS_ENGINE_CONFIG,
        tts_config=TTS_ENGINE_KWARGS
    )
    print("PDFProcessor initialized successfully")
    processor_available = True
except Exception as e:
    print(f"CRITICAL: PDFProcessor initialization failed: {e}")
    pdf_processor = None
    processor_available = False
    SELECTED_TTS_ENGINE = f"{_SELECTED_TTS_ENGINE_CONFIG.upper()} (Failed to Load)"

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- Flask Routes ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/audio_outputs/<filename>')
def serve_audio(filename):
    return send_from_directory(app.config['AUDIO_FOLDER'], filename)

@app.route('/get_pdf_info', methods=['POST'])
def get_pdf_info():
    """API endpoint to get PDF information after file upload"""
    if not processor_available or pdf_processor is None:
        return jsonify({'error': 'PDF Processor not available'}), 500
    
    if 'pdf_file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['pdf_file']
    if file.filename == '' or not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file'}), 400
    
    try:
        # Save temporary file to get info
        original_filename = secure_filename(file.filename)
        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], f"temp_{original_filename}")
        file.save(temp_path)
        
        # Get PDF info
        pdf_info = pdf_processor.get_pdf_info(temp_path)
        
        # Clean up temp file
        try:
            os.remove(temp_path)
        except:
            pass
        
        return jsonify(pdf_info)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/upload', methods=['POST'])
def upload_file():
    if not processor_available or pdf_processor is None:
        return f"Error: PDF Processor ({SELECTED_TTS_ENGINE}) is not available. Please check server logs."

    if request.method == 'POST':
        if 'pdf_file' not in request.files:
            return "No file part in the request."
        
        file = request.files['pdf_file']
        if file.filename == '':
            return "No file selected."
        
        if file and allowed_file(file.filename):
            original_filename = secure_filename(file.filename)
            base_filename_no_ext = os.path.splitext(original_filename)[0]
            
            # Save uploaded file
            pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], original_filename)
            file.save(pdf_path)
            
            # Get page range parameters
            use_page_range = request.form.get('use_page_range') == 'on'
            start_page = None
            end_page = None
            page_range_description = ""
            
            if use_page_range:
                try:
                    start_page_str = request.form.get('start_page', '').strip()
                    end_page_str = request.form.get('end_page', '').strip()
                    
                    if start_page_str:
                        start_page = int(start_page_str)
                        if start_page < 1:
                            return "Error: Start page must be 1 or greater."
                    
                    if end_page_str:
                        end_page = int(end_page_str)
                        if end_page < 1:
                            return "Error: End page must be 1 or greater."
                    
                    # Validate page range consistency
                    if start_page and end_page and start_page > end_page:
                        return "Error: Start page cannot be greater than end page."
                    
                    # Validate against actual PDF
                    validation = pdf_processor.validate_page_range(pdf_path, start_page, end_page)
                    if not validation.get('valid', False):
                        return f"Error: {validation.get('error', 'Invalid page range')}"
                    
                    # Build description for display
                    actual_start = validation.get('actual_start', start_page or 1)
                    actual_end = validation.get('actual_end', end_page)
                    total_pages = validation.get('total_pages', 0)
                    pages_to_process = validation.get('pages_to_process', 0)
                    
                    page_range_description = f" (pages {actual_start}-{actual_end} of {total_pages}, processing {pages_to_process} pages)"
                    
                    print(f"Processing with validated page range: {actual_start} to {actual_end}")
                    
                except ValueError:
                    return "Error: Invalid page numbers. Please enter valid integers."
                except Exception as e:
                    return f"Error validating page range: {str(e)}"
            
            print(f"Processing PDF: {original_filename}{page_range_description}")
            
            # Process the PDF with page range
            try:
                result = pdf_processor.process_pdf(pdf_path, base_filename_no_ext, start_page, end_page)
            except Exception as e:
                print(f"Processing error: {e}")
                result = None
            
            # Clean up uploaded PDF
            try:
                os.remove(pdf_path)
            except:
                pass
            
            if result and result.success:
                # Build display filename with page range info
                display_filename = original_filename + page_range_description
                
                return render_template('result.html', 
                                     audio_files=result.audio_files,           
                                     audio_file=result.audio_files[0],         
                                     original_filename=display_filename,
                                     tts_engine=SELECTED_TTS_ENGINE,
                                     file_count=len(result.audio_files),
                                     debug_info=result.debug_info)
            else:
                error_msg = result.error if result else "Unknown processing error"
                return f"Error: {error_msg}"
        else:
            return "Invalid file type. Please upload a PDF file."
    
    return redirect(url_for('index'))

@app.errorhandler(413)
def too_large(e):
    return "File is too large. Maximum file size is 100MB.", 413

@app.errorhandler(Exception)
def handle_exception(e):
    print(f"Unhandled exception: {e}")
    import traceback
    traceback.print_exc()
    return f"An error occurred: {str(e)}", 500

if __name__ == '__main__':
    print("Starting Flask development server...")
    print(f"TTS Engine: {SELECTED_TTS_ENGINE}")
    print(f"Upload folder: {UPLOAD_FOLDER}")
    print(f"Audio folder: {AUDIO_FOLDER}")
    app.run(debug=True, host='0.0.0.0', port=5000)