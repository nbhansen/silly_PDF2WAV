# app.py - Updated with TTSConfig system
import os
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, jsonify
from werkzeug.utils import secure_filename
from tts_utils import TTSConfig, CoquiConfig, GTTSConfig, BarkConfig, GeminiConfig

# --- Load environment variables ---
from dotenv import load_dotenv
load_dotenv()

# Import the new config system and processor architecture
from tts_utils import TTSConfig, CoquiConfig, GTTSConfig, BarkConfig
from processors import PDFProcessor

# --- Configuration ---
UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'uploads')
AUDIO_FOLDER = os.getenv('AUDIO_FOLDER', 'audio_outputs')
ALLOWED_EXTENSIONS = set(os.getenv('ALLOWED_EXTENSIONS', 'pdf').split(','))

GOOGLE_AI_API_KEY = os.getenv('GOOGLE_AI_API_KEY', '')

# --- TTS Engine Configuration ---
def create_tts_config() -> tuple[TTSConfig, str]:
    """Create TTS config and return config + engine name for display"""
    engine = os.getenv('TTS_ENGINE', 'coqui').lower()
    
    if engine == "coqui":
        config = TTSConfig(
            voice_quality=os.getenv('VOICE_QUALITY', 'medium'),
            coqui=CoquiConfig(
                model_name=os.getenv('COQUI_MODEL_NAME'),
                use_gpu=os.getenv('COQUI_USE_GPU_IF_AVAILABLE', 'True').lower() == 'true'
            )
        )
        return config, "Coqui TTS"
    elif engine == "gtts":
        config = TTSConfig(
            voice_quality=os.getenv('VOICE_QUALITY', 'medium'),
            gtts=GTTSConfig(
                lang=os.getenv('GTTS_LANG', 'en'),
                tld=os.getenv('GTTS_TLD', 'co.uk')
            )
        )
        return config, "gTTS"
    elif engine == "bark":
        config = TTSConfig(
            voice_quality=os.getenv('VOICE_QUALITY', 'medium'),
            bark=BarkConfig(
                use_gpu=os.getenv('BARK_USE_GPU_IF_AVAILABLE', 'True').lower() == 'true',
                use_small_models=os.getenv('BARK_USE_SMALL_MODELS', 'True').lower() == 'true',
                history_prompt=os.getenv('BARK_HISTORY_PROMPT', None)
            )
        )
        return config, "Bark"
    elif engine == "gemini":
        config = TTSConfig(
            voice_quality=os.getenv('VOICE_QUALITY', 'medium'),
            speaking_style=os.getenv('SPEAKING_STYLE', 'professional'),
            gemini=GeminiConfig(
                voice_name=os.getenv('GEMINI_VOICE_NAME'),
                style_prompt=os.getenv('GEMINI_STYLE_PROMPT'),
                api_key=GOOGLE_AI_API_KEY
            )
        )
        return config, "Gemini TTS"
    else:
        # Unknown engine, use defaults
        return TTSConfig(), f"{engine.upper()} (Unknown)"

tts_config, selected_tts_engine = create_tts_config()
SELECTED_TTS_ENGINE = selected_tts_engine

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
        tts_engine=os.getenv('TTS_ENGINE', 'coqui').lower(),
        tts_config=tts_config
    )
    print("PDFProcessor initialized successfully")
    processor_available = True
except Exception as e:
    print(f"CRITICAL: PDFProcessor initialization failed: {e}")
    pdf_processor = None
    processor_available = False
    SELECTED_TTS_ENGINE = f"{SELECTED_TTS_ENGINE} (Failed to Load)"

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
                
                # Debug: Print what we got from the processor
                print(f"DEBUG: audio_files = {result.audio_files}")
                print(f"DEBUG: combined_mp3_file = {result.combined_mp3_file}")
                print(f"DEBUG: debug_info = {result.debug_info}")
                
                return render_template('result.html', 
                                     audio_files=result.audio_files or [],           
                                     audio_file=result.audio_files[0] if result.audio_files else None,
                                     combined_mp3_file=result.combined_mp3_file,
                                     original_filename=display_filename,
                                     tts_engine=SELECTED_TTS_ENGINE,
                                     file_count=len(result.audio_files) if result.audio_files else 0,
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