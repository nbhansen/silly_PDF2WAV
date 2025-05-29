# app.py (completely refactored)
import os
from flask import Flask, render_template, request, redirect, url_for, send_from_directory
from werkzeug.utils import secure_filename

# Import the new processor architecture
from processors import PDFProcessor

# --- Configuration ---
UPLOAD_FOLDER = 'uploads'
AUDIO_FOLDER = 'audio_outputs'
ALLOWED_EXTENSIONS = {'pdf'}

# !! IMPORTANT !! Replace with your actual API key
GOOGLE_AI_API_KEY = "damngirl"  # Your key

# --- TTS Engine Configuration ---
_SELECTED_TTS_ENGINE_CONFIG = "coqui"  # or "gtts", "bark"
TTS_ENGINE_KWARGS = {}

if _SELECTED_TTS_ENGINE_CONFIG.lower() == "coqui":
    TTS_ENGINE_KWARGS = {
        "model_name": "tts_models/en/vctk/vits", 
        "use_gpu_if_available": True,
        "speaker_idx_to_use": "p227"
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

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(AUDIO_FOLDER, exist_ok=True)

# Initialize the new PDFProcessor (replaces all the old processors)
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
            
            print(f"Processing PDF: {original_filename}")
            
            # Use the new processor
            result = pdf_processor.process_pdf(pdf_path, base_filename_no_ext)
            
            # Clean up uploaded PDF
            try:
                os.remove(pdf_path)
            except:
                pass
            
            if result.success:
                return render_template('result.html', 
                                     audio_files=result.audio_files,           # List of files
                                     audio_file=result.audio_files[0],         # First file for compatibility  
                                     original_filename=original_filename,
                                     tts_engine=SELECTED_TTS_ENGINE,
                                     file_count=len(result.audio_files))
            else:
                return f"Error: {result.error}"
        else:
            return "Invalid file type. Please upload a PDF file."
    
    return redirect(url_for('index'))

if __name__ == '__main__':
    print("Starting Flask development server...")
    app.run(debug=True, host='0.0.0.0', port=5000)